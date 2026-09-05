"""
One Zerodha websocket connection, from handshake to reconnection.

This owns a single socket and nothing else. It connects, subscribes, sets the mode, hands every frame it reads to a callback, and reconnects when the connection drops. It does not decode frames, write them anywhere, or decide which instruments to carry, all of which belong to the shard that drives it.

Two things here are less obvious than they look. The first is that Zerodha remembers nothing across a reconnection, so every reconnect resubscribes the full token list and sets the mode again; a connection that came back without doing that would sit there healthy and silent. The second is that a refused connection has four different signatures, only one of which is an exception, and telling them apart is what lets the supervisor discover how many connections the account really allows.
"""

import asyncio
import json
import time

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

WEBSOCKET_ROOT = "wss://ws.kite.trade"
KITE_VERSION_HEADERS = {
    "X-Kite-Version": "3",
}

MODE_LTP = "ltp"
MODE_QUOTE = "quote"
MODE_FULL = "full"

SUBSCRIBE_BATCH_SIZE = 500
PING_INTERVAL_SECONDS = 2.5
PING_TIMEOUT_SECONDS = 5.0
OPEN_TIMEOUT_SECONDS = 30.0
CLOSE_TIMEOUT_SECONDS = 5.0
MAXIMUM_FRAME_BYTES = 16 * 1024 * 1024

INITIAL_RECONNECT_SECONDS = 2.0
MAXIMUM_RECONNECT_SECONDS = 60.0
EARLY_CLOSE_SECONDS = 10.0

REFUSAL_CLOSE_CODES = (1008, 1011, 1013)
REFUSAL_STATUS_CODES = (429, 503)
AUTHENTICATION_STATUS_CODES = (401, 403)


class ZerodhaConnectionError(Exception):
    """
    Raised when a websocket connection cannot be established or maintained.
    """


class ZerodhaAuthenticationError(ZerodhaConnectionError):
    """
    Raised when Zerodha rejects the credentials themselves rather than the connection.

    This is kept apart from a refusal because the responses are opposite. A refusal means the account is at its connection limit and the right move is to stop opening more and carry on with the ones that worked. An authentication failure means the access token is wrong, no number of connections will work, and retrying is both pointless and the fastest way to draw attention to the account.
    """


class ZerodhaConnectionRefusedError(ZerodhaConnectionError):
    """
    Raised when Zerodha accepts the credentials but will not give out this connection.

    Carries the evidence that led to the conclusion, so the supervisor can record why it stopped opening connections rather than only that it did.
    """

    def __init__(self, reason, detail):
        """
        Record why a connection was judged refused.

        Args:
            reason (str): A short machine-readable reason, for example "handshake_status_429" or "early_close_1008".
            detail (str): A human-readable description for the log.

        Returns:
            None.
        """
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def websocket_url(api_key, access_token):
    """
    Build the websocket URL for a set of credentials.

    Args:
        api_key (str): The Zerodha Kite Connect API key.
        access_token (str): An access token issued today.

    Returns:
        str: The full wss URL including both query parameters.
    """
    return f"{WEBSOCKET_ROOT}?api_key={api_key}&access_token={access_token}"


def subscribe_message(instrument_tokens):
    """
    Build the JSON message that subscribes to a list of instruments.

    Args:
        instrument_tokens (list[int]): The instrument tokens to subscribe to.

    Returns:
        str: The message to send.
    """
    return json.dumps({
        "a": "subscribe",
        "v": instrument_tokens,
    })


def unsubscribe_message(instrument_tokens):
    """
    Build the JSON message that unsubscribes from a list of instruments.

    Args:
        instrument_tokens (list[int]): The instrument tokens to unsubscribe from.

    Returns:
        str: The message to send.
    """
    return json.dumps({
        "a": "unsubscribe",
        "v": instrument_tokens,
    })


def mode_message(mode, instrument_tokens):
    """
    Build the JSON message that sets the streaming mode for a list of instruments.

    A bare subscribe puts instruments into quote mode, so full mode always needs this message as well. Note that the value is a two element array holding the mode and then the token list, which is a different shape from the subscribe and unsubscribe messages.

    Args:
        mode (str): One of "ltp", "quote" or "full".
        instrument_tokens (list[int]): The instrument tokens to apply the mode to.

    Returns:
        str: The message to send.
    """
    return json.dumps({
        "a": "mode",
        "v": [
            mode,
            instrument_tokens,
        ],
    })


class ZerodhaConnection:
    """
    Drives one Zerodha websocket connection and keeps it subscribed.

    Attributes:
        instrument_tokens (list[int]): The tokens this connection carries.
        mode (str): The streaming mode requested for them.
        connected (bool): Whether a socket is currently open.
        frames_received (int): Binary frames read since the object was created, including heartbeats.
        data_frames_received (int): Binary frames carrying at least one packet.
        heartbeats_received (int): One byte heartbeat frames read.
        bytes_received (int): Total bytes of binary frames read.
        text_messages_received (int): Text frames read, which are order updates, errors and broker messages.
        reconnect_count (int): Times this object has reconnected since it was created.
        last_data_frame_at (float | None): Monotonic time of the most recent frame carrying data, or None if there has not been one.
    """

    def __init__(self, api_key, access_token, instrument_tokens, on_frame, mode=MODE_FULL, on_text=None, logger=None, maximum_reconnect_attempts=None):
        """
        Prepare a connection without opening it.

        Args:
            api_key (str): The Zerodha Kite Connect API key.
            access_token (str): An access token issued today.
            instrument_tokens (list[int]): The instrument tokens this connection should carry.
            on_frame (collections.abc.Callable): Called as on_frame(arrival_time_nanoseconds, frame) for every binary frame, including heartbeats. It must not block, because it runs on the socket read path.
            mode (str): The streaming mode to request, one of "ltp", "quote" or "full".
            on_text (collections.abc.Callable | None): Called as on_text(message) for every text frame, or None to ignore them.
            logger (logging.Logger | None): Where to report connection events, or None to stay silent.
            maximum_reconnect_attempts (int | None): Give up after this many consecutive failures, or None to keep trying until stopped. Zero means do not reconnect at all, which is what capacity probing wants.

        Returns:
            None.
        """
        self.api_key = api_key
        self.access_token = access_token
        self.instrument_tokens = list(instrument_tokens)
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
        self.reconnect_count = 0
        self.last_data_frame_at = None
        self.connected_at = None
        self.ever_connected = False

    def seconds_since_last_data_frame(self):
        """
        Say how long it has been since a frame carrying actual data arrived.

        Heartbeats are excluded deliberately. Zerodha keeps sending them on a connection it has accepted but is not serving, so a connection that is subscribed, open, and silent apart from heartbeats is the signature of a subscription that was accepted and then quietly not honoured. This is the number that detects it.

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

    async def _send_subscription(self, websocket):
        """
        Subscribe every token this connection carries and set the requested mode.

        Tokens are sent in batches rather than as one enormous message, because a subscription of several thousand tokens produces a JSON array of a size Zerodha does not document a limit for, and a batch that is refused is easier to attribute than a single message that is.

        Both the subscribe and the mode message are sent on every connection, including reconnections, because Zerodha retains no subscription state across connections.

        Args:
            websocket: The open websocket connection to send on.

        Returns:
            None.

        Raises:
            websockets.exceptions.ConnectionClosed: If the connection drops while subscribing.
        """
        for start in range(0, len(self.instrument_tokens), SUBSCRIBE_BATCH_SIZE):
            batch = self.instrument_tokens[start:start + SUBSCRIBE_BATCH_SIZE]
            await websocket.send(subscribe_message(batch))
            await websocket.send(mode_message(self.mode, batch))

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

        if payload.get("type") == "error":
            self._log("error", f"Zerodha sent an error: {payload.get('data')}")
        elif payload.get("type") == "message":
            self._log("info", f"Zerodha sent a message: {payload.get('data')}")

        if self.on_text is not None:
            self.on_text(payload)

    async def _run_one_session(self, stop_event):
        """
        Open one connection, subscribe, and read frames until it closes or is stopped.

        Args:
            stop_event (asyncio.Event): Set this to ask the session to close cleanly.

        Returns:
            None.

        Raises:
            ZerodhaAuthenticationError: If Zerodha rejected the credentials.
            ZerodhaConnectionRefusedError: If Zerodha refused this connection, whether by handshake status or by closing it immediately after accepting it.
            websockets.exceptions.ConnectionClosed: If an established connection dropped for an ordinary reason.
        """
        try:
            websocket = await connect(
                websocket_url(self.api_key, self.access_token),
                additional_headers=KITE_VERSION_HEADERS,
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
                raise ZerodhaAuthenticationError(
                    f"Zerodha rejected the credentials with status {status_code}. The access token is most likely expired or was issued for a different API key."
                ) from error
            raise ZerodhaConnectionRefusedError(
                f"handshake_status_{status_code}",
                f"Zerodha refused the handshake with status {status_code}.",
            ) from error

        self.connected = True
        self.ever_connected = True
        self.connected_at = time.monotonic()
        self._log("info", f"connected, subscribing {len(self.instrument_tokens)} instruments in {self.mode} mode")

        try:
            await self._send_subscription(websocket)
            async for message in websocket:
                arrival_time_nanoseconds = time.time_ns()
                if isinstance(message, bytes):
                    self.frames_received = self.frames_received + 1
                    self.bytes_received = self.bytes_received + len(message)
                    if len(message) < 2:
                        self.heartbeats_received = self.heartbeats_received + 1
                    else:
                        self.data_frames_received = self.data_frames_received + 1
                        self.last_data_frame_at = time.monotonic()
                    self.on_frame(arrival_time_nanoseconds, message)
                else:
                    self._handle_text(message)
                if stop_event.is_set():
                    break
        except ConnectionClosed as error:
            open_for = time.monotonic() - self.connected_at
            code = getattr(getattr(error, "rcvd", None), "code", None)
            if open_for < EARLY_CLOSE_SECONDS and code in REFUSAL_CLOSE_CODES:
                raise ZerodhaConnectionRefusedError(
                    f"early_close_{code}",
                    f"Zerodha closed the connection with code {code} after {open_for:.1f} seconds, which is how it refuses a connection it has already accepted.",
                ) from error
            raise
        finally:
            self.connected = False
            await websocket.close()

    async def run(self, stop_event):
        """
        Keep a connection open until asked to stop, reconnecting with backoff when it drops.

        Every reconnection resubscribes from scratch, because Zerodha remembers no subscription state across connections and a reconnected socket would otherwise stay open and permanently silent.

        The backoff starts at two seconds and doubles to a minute. It is deliberately unhurried: this design runs many more connections than Zerodha documents, so a tight retry loop against a broker that has just refused one is the behaviour most likely to cost the account.

        Args:
            stop_event (asyncio.Event): Set this to bring the connection down cleanly and return.

        Returns:
            None.

        Raises:
            ZerodhaAuthenticationError: If the credentials were rejected, which no amount of retrying will fix.
            ZerodhaConnectionRefusedError: If Zerodha refused the connection, so the caller can record that its limit has been found.
            ZerodhaConnectionError: If the reconnection attempt limit was reached.
        """
        delay = INITIAL_RECONNECT_SECONDS
        consecutive_failures = 0

        while not stop_event.is_set():
            try:
                await self._run_one_session(stop_event)
                consecutive_failures = 0
                delay = INITIAL_RECONNECT_SECONDS
            except (ZerodhaAuthenticationError, ZerodhaConnectionRefusedError):
                raise
            except (ConnectionClosed, OSError, asyncio.TimeoutError) as error:
                consecutive_failures = consecutive_failures + 1
                self._log("warning", f"connection lost ({type(error).__name__}: {error}); reconnecting in {delay:.0f}s")

            if stop_event.is_set():
                break

            if self.maximum_reconnect_attempts == 0:
                return
            if self.maximum_reconnect_attempts is not None and consecutive_failures > self.maximum_reconnect_attempts:
                raise ZerodhaConnectionError(
                    f"gave up after {consecutive_failures} consecutive reconnection failures."
                )

            self.reconnect_count = self.reconnect_count + 1
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            delay = min(delay * 2, MAXIMUM_RECONNECT_SECONDS)
