"""
One Dhan live market feed websocket connection, from handshake to reconnection.

This owns a single socket and nothing else, exactly as its Zerodha counterpart does. It connects, subscribes in one of the three feed modes, hands every frame it reads to a callback, and reconnects when the connection drops. It does not decode frames, write them anywhere, or decide which instruments to carry, all of which belong to the shard that drives it.

Three things here are less obvious than they look. The first is that Dhan authenticates entirely in the URL, so there are no handshake headers at all, and the access token must be URL quoted because a JWT carries characters a query string would otherwise misread. The second is that the written documentation lists a connect request code, but Dhan's own client library sends no connect packet on the version two feed, it subscribes immediately, so neither do we; the code is kept as a constant in case a first live run shows a subscription being silently ignored. The third is that Dhan does not refuse a sixth websocket, it closes the oldest healthy one with disconnect reason 805, so the connection budget is a real budget: the live feed sockets and the depth sockets together must stay at or below the measured count, and a supervisor that keeps opening connections on an 805 is churning its own siblings.
"""

import asyncio
import json
import time
from urllib.parse import quote

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from stream.dhan import packets

WEBSOCKET_ROOT = "wss://api-feed.dhan.co"
AUTH_TYPE = 2

MODE_TICKER = "ticker"
MODE_QUOTE = "quote"
MODE_FULL = "full"

REQUEST_CODE_CONNECT = 11
REQUEST_CODE_DISCONNECT = 12
REQUEST_CODE_SUBSCRIBE_TICKER = 15
REQUEST_CODE_UNSUBSCRIBE_TICKER = 16
REQUEST_CODE_SUBSCRIBE_QUOTE = 17
REQUEST_CODE_UNSUBSCRIBE_QUOTE = 18
REQUEST_CODE_SUBSCRIBE_FULL = 21
REQUEST_CODE_UNSUBSCRIBE_FULL = 22

MODE_REQUEST_CODES = {
    MODE_TICKER: REQUEST_CODE_SUBSCRIBE_TICKER,
    MODE_QUOTE: REQUEST_CODE_SUBSCRIBE_QUOTE,
    MODE_FULL: REQUEST_CODE_SUBSCRIBE_FULL,
}

EXCHANGE_SEGMENT_NAMES = {
    0: "IDX_I",
    1: "NSE_EQ",
    2: "NSE_FNO",
    3: "NSE_CURRENCY",
    4: "BSE_EQ",
    5: "MCX_COMM",
    7: "BSE_CURRENCY",
    8: "BSE_FNO",
}

SUBSCRIBE_BATCH_SIZE = 100
PING_INTERVAL_SECONDS = 20.0
PING_TIMEOUT_SECONDS = 10.0
OPEN_TIMEOUT_SECONDS = 30.0
CLOSE_TIMEOUT_SECONDS = 5.0
MAXIMUM_FRAME_BYTES = 16 * 1024 * 1024

INITIAL_RECONNECT_SECONDS = 2.0
MAXIMUM_RECONNECT_SECONDS = 60.0
EARLY_CLOSE_SECONDS = 10.0

REFUSAL_CLOSE_CODES = (1008, 1011, 1013)
REFUSAL_STATUS_CODES = (429, 503)
AUTHENTICATION_STATUS_CODES = (401, 403)


class DhanConnectionError(Exception):
    """
    Raised when a websocket connection cannot be established or maintained.
    """


class DhanAuthenticationError(DhanConnectionError):
    """
    Raised when Dhan rejects the credentials themselves rather than the connection.

    This is kept apart from a refusal because the responses are opposite. A refusal means the account is at its connection limit and the right move is to stop opening more and carry on with the ones that worked. An authentication failure means the token or client identifier is wrong, no number of connections will work, and retrying is both pointless and the fastest way to draw attention to the account.
    """


class DhanConnectionRefusedError(DhanConnectionError):
    """
    Raised when Dhan accepts the credentials but will not serve this connection, or has evicted it to make room for another.

    Carries the evidence that led to the conclusion, so the supervisor can record why it stopped opening connections rather than only that it did. Unlike Zerodha, whose refusals have to be inferred from handshake statuses and close codes, Dhan usually says why, in a disconnect packet carrying a reason code.
    """

    def __init__(self, reason, detail):
        """
        Record why a connection was judged refused.

        Args:
            reason (str): A short machine-readable reason, for example "handshake_status_429" or "disconnect_reason_805".
            detail (str): A human-readable description for the log.

        Returns:
            None.
        """
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def websocket_url(client_id, access_token):
    """
    Build the websocket URL for a set of credentials.

    Both credentials go in the query string, and both are URL quoted, because an access token is a JWT whose characters include ones a query string would otherwise misread.

    Args:
        client_id (str): The Dhan client identifier.
        access_token (str): An access token issued today.

    Returns:
        str: The full wss URL including every query parameter Dhan requires.
    """
    return f"{WEBSOCKET_ROOT}?version=2&token={quote(access_token)}&clientId={quote(client_id)}&authType={AUTH_TYPE}"


def subscribe_message(request_code, instruments):
    """
    Build the JSON message that subscribes a list of instruments in one feed mode.

    The mode is chosen by the request code, and the instrument count must equal the list length, which Dhan checks. Dhan identifies instruments by exchange segment and security id rather than by one integer token, and the segment must be spelled the way the wire expects, which is the table this module owns rather than the short names the decoder owns.

    Args:
        request_code (int): The subscribe request code, one of 15 for ticker, 17 for quote or 21 for full.
        instruments (list[tuple]): One (exchange_segment, security_id) pair per instrument, where the segment is the numeric byte code.

    Returns:
        str: The message to send.

    Raises:
        KeyError: If an exchange segment is not one Dhan documents, which means the caller is carrying an instrument this module cannot name.
    """
    instrument_list = []
    for exchange_segment, security_id in instruments:
        instrument_list.append({
            "ExchangeSegment": EXCHANGE_SEGMENT_NAMES[exchange_segment],
            "SecurityId": str(security_id),
        })
    return json.dumps({
        "RequestCode": request_code,
        "InstrumentCount": len(instrument_list),
        "InstrumentList": instrument_list,
    })


def unsubscribe_message(request_code, instruments):
    """
    Build the JSON message that unsubscribes a list of instruments from one feed mode.

    Args:
        request_code (int): The unsubscribe request code, 16 for ticker, 18 for quote or 22 for full.
        instruments (list[tuple]): One (exchange_segment, security_id) pair per instrument.

    Returns:
        str: The message to send.

    Raises:
        KeyError: If an exchange segment is not one Dhan documents.
    """
    return subscribe_message(request_code, instruments)


def disconnect_message():
    """
    Build the JSON message that asks the feed to close.

    Args:
        None.

    Returns:
        str: The message to send.
    """
    return json.dumps({
        "RequestCode": REQUEST_CODE_DISCONNECT,
    })


class DhanConnection:
    """
    Drives one Dhan live market feed websocket connection and keeps it subscribed.

    Attributes:
        instruments (list[tuple]): The (exchange_segment, security_id) pairs this connection carries.
        mode (str): The feed mode requested for them.
        connected (bool): Whether a socket is currently open.
        frames_received (int): Binary frames read since the object was created, including disconnect packets.
        data_frames_received (int): Binary frames carrying at least one packet.
        heartbeats_received (int): Frames too short to carry a header.
        bytes_received (int): Total bytes of binary frames read.
        text_messages_received (int): Text frames read, which are errors and broker messages.
        disconnect_packets_received (int): Disconnect packets read, whether or not they ended the session.
        reconnect_count (int): Times this object has reconnected since it was created.
        last_data_frame_at (float | None): Monotonic time of the most recent frame carrying data, or None if there has not been one.
    """

    def __init__(self, client_id, access_token, instruments, on_frame, mode=MODE_FULL, on_text=None, logger=None, maximum_reconnect_attempts=None):
        """
        Prepare a connection without opening it.

        Args:
            client_id (str): The Dhan client identifier.
            access_token (str): An access token issued today.
            instruments (list[tuple]): The (exchange_segment, security_id) pairs this connection should carry.
            on_frame (collections.abc.Callable): Called as on_frame(arrival_time_nanoseconds, frame) for every binary frame, including disconnect packets. It must not block, because it runs on the socket read path.
            mode (str): The feed mode to request, one of "ticker", "quote" or "full".
            on_text (collections.abc.Callable | None): Called as on_text(message) for every text frame, or None to ignore them.
            logger (logging.Logger | None): Where to report connection events, or None to stay silent.
            maximum_reconnect_attempts (int | None): Give up after this many consecutive failures, or None to keep trying until stopped. Zero means do not reconnect at all, which is what capacity probing wants.

        Returns:
            None.
        """
        self.client_id = client_id
        self.access_token = access_token
        self.instruments = list(instruments)
        self.on_frame = on_frame
        self.mode = mode
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

        Frames too short to carry a header are excluded deliberately. A connection that is subscribed, open, and silent apart from such frames is the signature of a subscription that was accepted and then quietly not honoured, and this is the number that detects it.

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

        The reasons Dhan names split into two answers. An expired token, an invalid client identifier or a failed authentication means no connection will ever work with these credentials, and that is an authentication failure. Exceeding the connection limit or lacking the data entitlement means the credentials are fine and this particular connection was one too many or one too unentitled, and that is a refusal.

        Args:
            reason (str | None): The disconnect reason, for example "access_token_expired", or None when the packet carried an undocumented code.
            detail (str): A human-readable description for the log and the exception.

        Returns:
            None.

        Raises:
            DhanAuthenticationError: If the reason was one of the credential rejections.
            DhanConnectionRefusedError: If the reason was a connection limit or a missing entitlement, or an undocumented code treated as a refusal.
        """
        if reason in ("access_token_expired", "invalid_client_id", "authentication_failed"):
            raise DhanAuthenticationError(f"{reason}: {detail}")
        machine_reason = reason if reason is not None else "undocumented_disconnect_reason"
        raise DhanConnectionRefusedError(
            f"disconnect_{machine_reason}",
            detail,
        )

    async def _send_subscription(self, websocket):
        """
        Subscribe every instrument this connection carries, in the requested mode.

        Instruments are sent in batches rather than as one enormous message, because Dhan caps a subscription message at one hundred instruments and counts the instruments in it, so batching is the wire's own rule rather than a choice. The feed retains no subscription state across connections, so this runs on every connection including reconnections.

        Args:
            websocket: The open websocket connection to send on.

        Returns:
            None.

        Raises:
            websockets.exceptions.ConnectionClosed: If the connection drops while subscribing.
            KeyError: If an exchange segment is not one Dhan documents.
        """
        request_code = MODE_REQUEST_CODES[self.mode]
        for start in range(0, len(self.instruments), SUBSCRIBE_BATCH_SIZE):
            batch = self.instruments[start:start + SUBSCRIBE_BATCH_SIZE]
            await websocket.send(subscribe_message(request_code, batch))

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
        Run the accounting and callback for one binary frame, and raise when it is a disconnect packet.

        A disconnect packet is counted as a frame and handed to the callback before the exception is raised, so the archive holds the reason the connection ended. The heartbeat test is a frame shorter than the eight byte header, because Dhan sends no one byte heartbeats and any such frame cannot carry a packet.

        Args:
            message (bytes): The binary frame as received.

        Returns:
            None.

        Raises:
            DhanAuthenticationError: If the disconnect reason was one of the credential rejections.
            DhanConnectionRefusedError: If the disconnect reason was a connection limit, a missing entitlement, or an undocumented code.
        """
        arrival_time_nanoseconds = time.time_ns()
        self.frames_received = self.frames_received + 1
        self.bytes_received = self.bytes_received + len(message)

        if len(message) < packets.HEADER_LENGTH:
            self.heartbeats_received = self.heartbeats_received + 1
            self.on_frame(arrival_time_nanoseconds, message)
            return

        if packets.response_code(message) == packets.RESPONSE_CODE_DISCONNECT and len(message) >= packets.DISCONNECT_PACKET_LENGTH:
            self.disconnect_packets_received = self.disconnect_packets_received + 1
            reason = packets.decode_disconnect(message)
            self._log("warning", f"Dhan sent a disconnect packet with reason {reason}")
            self.on_frame(arrival_time_nanoseconds, message)
            self._raise_for_disconnect_reason(reason, f"Dhan closed the feed with disconnect reason {reason}.")
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
            DhanAuthenticationError: If Dhan rejected the credentials.
            DhanConnectionRefusedError: If Dhan refused this connection or evicted it, whether signalled by handshake status, by an early close, or by a disconnect packet.
            websockets.exceptions.ConnectionClosed: If an established connection dropped for an ordinary reason.
        """
        try:
            websocket = await connect(
                websocket_url(self.client_id, self.access_token),
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
                raise DhanAuthenticationError(
                    f"Dhan rejected the credentials with status {status_code}. The access token is most likely expired or was issued for a different client identifier."
                ) from error
            raise DhanConnectionRefusedError(
                f"handshake_status_{status_code}",
                f"Dhan refused the handshake with status {status_code}.",
            ) from error

        self.connected = True
        self.ever_connected = True
        self.connected_at = time.monotonic()
        self._log("info", f"connected, subscribing {len(self.instruments)} instruments in {self.mode} mode")

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
                raise DhanConnectionRefusedError(
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

        Every reconnection resubscribes from scratch, because Dhan remembers no subscription state across connections and a reconnected socket would otherwise stay open and permanently silent.

        The backoff starts at two seconds and doubles to a minute, and it matters more here than for Zerodha: Dhan does not refuse an excess connection, it evicts the oldest healthy one, so a tight retry loop on a connection that keeps being evicted would churn every sibling the account is running. A connection that reports disconnect reason 805 should stop the supervisor from opening further connections rather than be retried.

        Args:
            stop_event (asyncio.Event): Set this to bring the connection down cleanly and return.

        Returns:
            None.

        Raises:
            DhanAuthenticationError: If the credentials were rejected, which no amount of retrying will fix.
            DhanConnectionRefusedError: If Dhan refused the connection or evicted it, so the caller can record that its limit has been found.
            DhanConnectionError: If the reconnection attempt limit was reached.
        """
        delay = INITIAL_RECONNECT_SECONDS
        consecutive_failures = 0

        while not stop_event.is_set():
            try:
                await self._run_one_session(stop_event)
                consecutive_failures = 0
                delay = INITIAL_RECONNECT_SECONDS
            except (DhanAuthenticationError, DhanConnectionRefusedError):
                raise
            except (ConnectionClosed, OSError, asyncio.TimeoutError) as error:
                consecutive_failures = consecutive_failures + 1
                self._log("warning", f"connection lost ({type(error).__name__}: {error}); reconnecting in {delay:.0f}s")

            if stop_event.is_set():
                break

            if self.maximum_reconnect_attempts == 0:
                return
            if self.maximum_reconnect_attempts is not None and consecutive_failures > self.maximum_reconnect_attempts:
                raise DhanConnectionError(
                    f"gave up after {consecutive_failures} consecutive reconnection failures."
                )

            self.reconnect_count = self.reconnect_count + 1
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            delay = min(delay * 2, MAXIMUM_RECONNECT_SECONDS)