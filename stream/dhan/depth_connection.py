"""
One Dhan full market depth websocket connection, for either the twenty level or the two hundred level book.

This owns a single socket and nothing else, exactly as the live feed connection does. It connects, subscribes, hands every frame it reads to a callback, and reconnects when the connection drops. It does not decode frames, write them anywhere, or decide which instruments to carry.

The two depth sockets differ from each other in only three things: the URL, the shape of the subscription message, and what the header's last field means. Everything else, the wire format, the keep-alive behaviour, the disconnect reasons and the reconnection rules, is shared, which is why one class parameterised on depth level carries both rather than two near-identical classes. What cannot be parameterised away is the connection budget: the twenty level and two hundred level sockets and the live feed sockets all draw on the same pool of five, and a two hundred level socket spends one whole connection on one instrument, so it is built here but is not expected to carry anything more than a handful of watched symbols.
"""

import asyncio
import json
import time
from urllib.parse import quote

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from stream.dhan import depth_packets
from stream.dhan.connection import (
    AUTH_TYPE,
    AUTHENTICATION_STATUS_CODES,
    EARLY_CLOSE_SECONDS,
    INITIAL_RECONNECT_SECONDS,
    MAXIMUM_FRAME_BYTES,
    MAXIMUM_RECONNECT_SECONDS,
    OPEN_TIMEOUT_SECONDS,
    PING_INTERVAL_SECONDS,
    PING_TIMEOUT_SECONDS,
    REFUSAL_CLOSE_CODES,
    REQUEST_CODE_DISCONNECT,
    CLOSE_TIMEOUT_SECONDS,
)

TWENTY_DEPTH_WEBSOCKET_ROOT = "wss://depth-api-feed.dhan.co/twentydepth"
TWO_HUNDRED_DEPTH_WEBSOCKET_ROOT = "wss://full-depth-api.dhan.co/twohundreddepth"

REQUEST_CODE_SUBSCRIBE_DEPTH = 23
REQUEST_CODE_UNSUBSCRIBE_DEPTH = 24

TWENTY_DEPTH_LEVELS = 20
TWO_HUNDRED_DEPTH_LEVELS = 200
TWENTY_DEPTH_BATCH_SIZE = 50
TWO_HUNDRED_DEPTH_INSTRUMENTS = 1


class DhanDepthConnectionError(Exception):
    """
    Raised when a depth websocket connection cannot be established or maintained.
    """


class DhanDepthAuthenticationError(DhanDepthConnectionError):
    """
    Raised when Dhan rejects the credentials themselves rather than the connection.

    This mirrors the live feed's authentication error, and is kept apart from it so that a caller catching one broker's authentication failure does not accidentally catch the other's in a different module.
    """


class DhanDepthConnectionRefusedError(DhanDepthConnectionError):
    """
    Raised when Dhan accepts the credentials but will not serve this connection, or has evicted it to make room for another.

    Mirrors the live feed's refusal error and carries the same machine-readable evidence.
    """

    def __init__(self, reason, detail):
        """
        Record why a connection was judged refused.

        Args:
            reason (str): A short machine-readable reason, for example "handshake_status_429" or "disconnect_connection_limit_exceeded".
            detail (str): A human-readable description for the log.

        Returns:
            None.
        """
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def websocket_url(depth_level, client_id, access_token):
    """
    Build the websocket URL for one depth socket.

    Args:
        depth_level (int): The depth level to subscribe to, 20 or 200, which selects the socket's host.
        client_id (str): The Dhan client identifier.
        access_token (str): An access token issued today.

    Returns:
        str: The full wss URL including every query parameter Dhan requires.

    Raises:
        ValueError: If the depth level is neither 20 nor 200.
    """
    if depth_level == TWENTY_DEPTH_LEVELS:
        websocket_root = TWENTY_DEPTH_WEBSOCKET_ROOT
    elif depth_level == TWO_HUNDRED_DEPTH_LEVELS:
        websocket_root = TWO_HUNDRED_DEPTH_WEBSOCKET_ROOT
    else:
        raise ValueError(f"Depth level must be {TWENTY_DEPTH_LEVELS} or {TWO_HUNDRED_DEPTH_LEVELS}, not {depth_level}.")
    return f"{websocket_root}?token={quote(access_token)}&clientId={quote(client_id)}&authType={AUTH_TYPE}"


def subscribe_message(depth_level, instruments):
    """
    Build the JSON message that subscribes instruments on a depth socket.

    The two levels take differently shaped subscriptions. The twenty level socket takes an instrument list of at most fifty, with the instrument count matching it. The two hundred level socket takes exactly one instrument, named at the top level of the message rather than in a list, which is why the two hundred level connection can never carry more than one instrument.

    Args:
        depth_level (int): The depth level this message is for, 20 or 200.
        instruments (list[tuple]): One (exchange_segment, security_id) pair per instrument.

    Returns:
        str: The message to send.

    Raises:
        ValueError: If the depth level is neither 20 nor 200, or a two hundred level subscription does not carry exactly one instrument.
    """
    if depth_level == TWENTY_DEPTH_LEVELS:
        instrument_list = []
        for exchange_segment, security_id in instruments:
            instrument_list.append({
                "ExchangeSegment": depth_packets.SEGMENT_NAMES[exchange_segment].upper(),
                "SecurityId": str(security_id),
            })
        return json.dumps({
            "RequestCode": REQUEST_CODE_SUBSCRIBE_DEPTH,
            "InstrumentCount": len(instrument_list),
            "InstrumentList": instrument_list,
        })
    if depth_level == TWO_HUNDRED_DEPTH_LEVELS:
        if len(instruments) != TWO_HUNDRED_DEPTH_INSTRUMENTS:
            raise ValueError(
                f"The two hundred level socket carries exactly {TWO_HUNDRED_DEPTH_INSTRUMENTS} instrument, not {len(instruments)}."
            )
        exchange_segment, security_id = instruments[0]
        return json.dumps({
            "RequestCode": REQUEST_CODE_SUBSCRIBE_DEPTH,
            "ExchangeSegment": depth_packets.SEGMENT_NAMES[exchange_segment].upper(),
            "SecurityId": str(security_id),
        })
    raise ValueError(f"Depth level must be {TWENTY_DEPTH_LEVELS} or {TWO_HUNDRED_DEPTH_LEVELS}, not {depth_level}.")


def disconnect_message():
    """
    Build the JSON message that asks the depth feed to close.

    Args:
        None.

    Returns:
        str: The message to send.
    """
    return json.dumps({
        "RequestCode": REQUEST_CODE_DISCONNECT,
    })


class DhanDepthConnection:
    """
    Drives one Dhan full market depth websocket connection and keeps it subscribed.

    Attributes:
        depth_level (int): The depth level this connection subscribed to, 20 or 200.
        instruments (list[tuple]): The (exchange_segment, security_id) pairs this connection carries, at most fifty for a twenty level socket and exactly one for a two hundred level socket.
        connected (bool): Whether a socket is currently open.
        frames_received (int): Binary frames read since the object was created, including disconnect packets.
        data_frames_received (int): Binary frames carrying at least one bid or ask section.
        heartbeats_received (int): Frames too short to carry a header.
        bytes_received (int): Total bytes of binary frames read.
        text_messages_received (int): Text frames read, which are errors and broker messages.
        disconnect_packets_received (int): Disconnect packets read, whether or not they ended the session.
        reconnect_count (int): Times this object has reconnected since it was created.
        last_data_frame_at (float | None): Monotonic time of the most recent frame carrying data, or None if there has not been one.
    """

    def __init__(self, depth_level, client_id, access_token, instruments, on_frame, on_text=None, logger=None, maximum_reconnect_attempts=None):
        """
        Prepare a connection without opening it.

        Args:
            depth_level (int): The depth level to subscribe to, 20 or 200.
            client_id (str): The Dhan client identifier.
            access_token (str): An access token issued today.
            instruments (list[tuple]): The (exchange_segment, security_id) pairs this connection should carry.
            on_frame (collections.abc.Callable): Called as on_frame(arrival_time_nanoseconds, frame) for every binary frame, including disconnect packets. It must not block, because it runs on the socket read path.
            on_text (collections.abc.Callable | None): Called as on_text(message) for every text frame, or None to ignore them.
            logger (logging.Logger | None): Where to report connection events, or None to stay silent.
            maximum_reconnect_attempts (int | None): Give up after this many consecutive failures, or None to keep trying until stopped. Zero means do not reconnect at all, which is what capacity probing wants.

        Returns:
            None.

        Raises:
            ValueError: If the depth level is neither 20 nor 200, or a two hundred level connection is asked to carry anything but one instrument.
        """
        if depth_level not in (TWENTY_DEPTH_LEVELS, TWO_HUNDRED_DEPTH_LEVELS):
            raise ValueError(f"Depth level must be {TWENTY_DEPTH_LEVELS} or {TWO_HUNDRED_DEPTH_LEVELS}, not {depth_level}.")
        if depth_level == TWO_HUNDRED_DEPTH_LEVELS and len(instruments) != TWO_HUNDRED_DEPTH_INSTRUMENTS:
            raise ValueError(
                f"The two hundred level socket carries exactly {TWO_HUNDRED_DEPTH_INSTRUMENTS} instrument, not {len(instruments)}."
            )

        self.depth_level = depth_level
        self.client_id = client_id
        self.access_token = access_token
        self.instruments = list(instruments)
        self.on_frame = on_frame
        self.on_text = on_text
        self.logger = logger
        self.maximum_reconnect_attempts = maximum_reconnect_attempts

        self.connected = False
        self.frames_received = 0
        self.data_frames_received = 0
        self.heartbeats_received = 0
        self.bytes_received = 0
        self.text_messages_received = 0
        self.disconnect_packets_received = 0
        self.reconnect_count = 0
        self.last_data_frame_at = None
        self.connected_at = None
        self.ever_connected = False

    def seconds_since_last_data_frame(self):
        """
        Say how long it has been since a frame carrying actual data arrived.

        Returns:
            float | None: Seconds since the last data frame, or None when no data frame has ever arrived on this connection.
        """
        if self.last_data_frame_at is None:
            return None
        return time.monotonic() - self.last_data_frame_at

    def _log(self, level, message):
        """
        Report a connection event if a logger was supplied.

        Args:
            level (str): The logger method to call, for example "info" or "warning".
            message (str): The message to log.

        Returns:
            None.
        """
        if self.logger is not None:
            getattr(self.logger, level)(message)

    def _raise_for_disconnect_reason(self, reason, detail):
        """
        Turn a disconnect reason into the exception the supervisor should see.

        Args:
            reason (str | None): The disconnect reason, for example "access_token_expired", or None when the packet carried an undocumented code.
            detail (str): A human-readable description for the log and the exception.

        Returns:
            None.

        Raises:
            DhanDepthAuthenticationError: If the reason was one of the credential rejections.
            DhanDepthConnectionRefusedError: If the reason was a connection limit, a missing entitlement, or an undocumented code.
        """
        if reason in ("access_token_expired", "invalid_client_id", "authentication_failed"):
            raise DhanDepthAuthenticationError(f"{reason}: {detail}")
        machine_reason = reason if reason is not None else "undocumented_disconnect_reason"
        raise DhanDepthConnectionRefusedError(
            f"disconnect_{machine_reason}",
            detail,
        )

    async def _send_subscription(self, websocket):
        """
        Subscribe every instrument this connection carries.

        The twenty level socket caps a subscription at fifty instruments, and the two hundred level socket carries exactly one, enforced at construction, so the only batching this loop does is split a twenty level subscription into fifty instrument messages. The feed retains no subscription state across connections, so this runs on every connection including reconnections.

        Args:
            websocket: The open websocket connection to send on.

        Returns:
            None.

        Raises:
            websockets.exceptions.ConnectionClosed: If the connection drops while subscribing.
        """
        for start in range(0, len(self.instruments), TWENTY_DEPTH_BATCH_SIZE):
            batch = self.instruments[start:start + TWENTY_DEPTH_BATCH_SIZE]
            await websocket.send(subscribe_message(self.depth_level, batch))

    def _handle_text(self, message):
        """
        Deal with a text frame, which is never market data.

        Args:
            message (str): The text frame as received.

        Returns:
            None.
        """
        self.text_messages_received = self.text_messages_received + 1
        try:
            payload = json.loads(message)
        except ValueError:
            self._log("warning", f"unparseable text frame: {message[:200]}")
            return

        self._log("info", f"Dhan sent a text message: {str(payload)[:200]}")
        if self.on_text is not None:
            self.on_text(payload)

    def _handle_binary_frame(self, message):
        """
        Do the accounting and callback for one binary frame, and raise when it is a disconnect packet.

        A disconnect packet is counted and handed to the callback before the exception is raised, so the archive holds the reason the connection ended.

        Args:
            message (bytes): The binary frame as received.

        Returns:
            None.

        Raises:
            DhanDepthAuthenticationError: If the disconnect reason was one of the credential rejections.
            DhanDepthConnectionRefusedError: If the disconnect reason was a connection limit, a missing entitlement, or an undocumented code.
        """
        arrival_time_nanoseconds = time.time_ns()
        self.frames_received = self.frames_received + 1
        self.bytes_received = self.bytes_received + len(message)

        if len(message) < depth_packets.HEADER_LENGTH:
            self.heartbeats_received = self.heartbeats_received + 1
            self.on_frame(arrival_time_nanoseconds, message)
            return

        if message[2] == depth_packets.DISCONNECT_RESPONSE_CODE:
            self.disconnect_packets_received = self.disconnect_packets_received + 1
            reason = depth_packets.decode_disconnect(message)
            self._log("warning", f"Dhan sent a depth disconnect packet with reason {reason}")
            self.on_frame(arrival_time_nanoseconds, message)
            self._raise_for_disconnect_reason(reason, f"Dhan closed the depth feed with disconnect reason {reason}.")
            return

        self.data_frames_received = self.data_frames_received + 1
        self.last_data_frame_at = time.monotonic()
        self.on_frame(arrival_time_nanoseconds, message)

    async def _run_one_session(self, stop_event):
        """
        Open one connection, subscribe, and read frames until it closes or is stopped.

        Args:
            stop_event (asyncio.Event): Set this to ask the session to close cleanly.

        Returns:
            None.

        Raises:
            DhanDepthAuthenticationError: If Dhan rejected the credentials.
            DhanDepthConnectionRefusedError: If Dhan refused this connection or evicted it.
            websockets.exceptions.ConnectionClosed: If an established connection dropped for an ordinary reason.
        """
        try:
            websocket = await connect(
                websocket_url(self.depth_level, self.client_id, self.access_token),
                ping_interval=PING_INTERVAL_SECONDS,
                ping_timeout=PING_TIMEOUT_SECONDS,
                open_timeout=OPEN_TIMEOUT_SECONDS,
                close_timeout=CLOSE_TIMEOUT_SECONDS,
                max_size=MAXIMUM_FRAME_BYTES,
                compression=None,
            )
        except InvalidStatus as error:
            status_code = getattr(getattr(error, "response", None), "status_code", None)
            if status_code in AUTHENTICATION_STATUS_CODES and not self.ever_connected:
                raise DhanDepthAuthenticationError(
                    f"Dhan rejected the credentials with status {status_code}. The access token is most likely expired or was issued for a different client identifier."
                ) from error
            raise DhanDepthConnectionRefusedError(
                f"handshake_status_{status_code}",
                f"Dhan refused the handshake with status {status_code}.",
            ) from error

        self.connected = True
        self.ever_connected = True
        self.connected_at = time.monotonic()
        self._log("info", f"connected, subscribing {len(self.instruments)} instruments at {self.depth_level} depth levels")

        try:
            await self._send_subscription(websocket)
            async for message in websocket:
                if isinstance(message, bytes):
                    self._handle_binary_frame(message)
                else:
                    self._handle_text(message)
                if stop_event.is_set():
                    break
        except ConnectionClosed as error:
            open_for = time.monotonic() - self.connected_at
            code = getattr(getattr(error, "rcvd", None), "code", None)
            if open_for < EARLY_CLOSE_SECONDS and code in REFUSAL_CLOSE_CODES:
                raise DhanDepthConnectionRefusedError(
                    f"early_close_{code}",
                    f"Dhan closed the connection with code {code} after {open_for:.1f} seconds, which is how it refuses a connection it has already accepted.",
                ) from error
            raise
        finally:
            self.connected = False
            await websocket.close()

    async def run(self, stop_event):
        """
        Keep a connection open until asked to stop, reconnecting with backoff when it drops.

        Every reconnection resubscribes from scratch, and the same caution about evictions applies as on the live feed: Dhan does not refuse an excess connection, it closes the oldest healthy one, so a tight retry loop on an evicted depth socket churns its siblings.

        Args:
            stop_event (asyncio.Event): Set this to bring the connection down cleanly and return.

        Returns:
            None.

        Raises:
            DhanDepthAuthenticationError: If the credentials were rejected, which no amount of retrying will fix.
            DhanDepthConnectionRefusedError: If Dhan refused the connection or evicted it, so the caller can record that its limit has been found.
            DhanDepthConnectionError: If the reconnection attempt limit was reached.
        """
        delay = INITIAL_RECONNECT_SECONDS
        consecutive_failures = 0

        while not stop_event.is_set():
            try:
                await self._run_one_session(stop_event)
                consecutive_failures = 0
                delay = INITIAL_RECONNECT_SECONDS
            except (DhanDepthAuthenticationError, DhanDepthConnectionRefusedError):
                raise
            except (ConnectionClosed, OSError, asyncio.TimeoutError) as error:
                consecutive_failures = consecutive_failures + 1
                self._log("warning", f"connection lost ({type(error).__name__}: {error}); reconnecting in {delay:.0f}s")

            if stop_event.is_set():
                break

            if self.maximum_reconnect_attempts == 0:
                return
            if self.maximum_reconnect_attempts is not None and consecutive_failures > self.maximum_reconnect_attempts:
                raise DhanDepthConnectionError(
                    f"gave up after {consecutive_failures} consecutive reconnection failures."
                )

            self.reconnect_count = self.reconnect_count + 1
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            delay = min(delay * 2, MAXIMUM_RECONNECT_SECONDS)