"""
One Fyers tick-by-tick websocket connection, for the fifty level market depth book.

This owns a single socket and nothing else, exactly as the quote feed connection does. It connects, subscribes, resumes its channel, hands every frame it reads to a callback, and reconnects when the connection drops. It does not decode frames, write them anywhere, or decide which instruments to carry.

Almost everything about this socket is the opposite of the quote socket's. It authenticates with an ordinary header rather than in-band, its requests are JSON rather than a private binary layout, its replies are Protocol Buffers rather than positional fields, and Fyers documents all of it. What it does not do is carry many instruments: five per connection against three connections, so fifteen at a time, which is why this is built as a watched-symbol feed rather than a way to cover the universe. It stands in the same relation to the quote feed as Dhan's two hundred level depth socket does to its live feed.

The one trap is channels. Subscribing to a channel does not start data flowing; the channel also has to be resumed, in a separate message. A connection that subscribes and never resumes sits open, acknowledges nothing, and stays silent forever, which looks exactly like a subscription that was refused. `_send_subscription` therefore always sends both, in that order.
"""

import asyncio
import json
import time

import requests
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from stream.fyers import depth_packets

WEBSOCKET_ROOT = "wss://rtsocket-api.fyers.in/versova"
WEBSOCKET_DISCOVERY_URL = "https://api-t1.fyers.in/indus/home/tbtws"
DISCOVERY_TIMEOUT_SECONDS = 10.0

REQUEST_TYPE_SUBSCRIPTION = 1
REQUEST_TYPE_SWITCH_CHANNEL = 2

SUBSCRIBE_FLAG = 1
UNSUBSCRIBE_FLAG = -1

DEPTH_MODE = "depth"
DEFAULT_CHANNEL = "1"

KEEP_ALIVE_MESSAGE = "ping"
KEEP_ALIVE_INTERVAL_SECONDS = 10.0

DOCUMENTED_SYMBOLS_PER_CONNECTION = 5
DOCUMENTED_CONNECTIONS_PER_USER = 3

PING_INTERVAL_SECONDS = 20.0
PING_TIMEOUT_SECONDS = 10.0
OPEN_TIMEOUT_SECONDS = 30.0
CLOSE_TIMEOUT_SECONDS = 5.0
MAXIMUM_FRAME_BYTES = 16 * 1024 * 1024

INITIAL_RECONNECT_SECONDS = 2.0
MAXIMUM_RECONNECT_SECONDS = 60.0
EARLY_CLOSE_SECONDS = 10.0

REFUSAL_CLOSE_CODES = (1008, 1011, 1013)
AUTHENTICATION_STATUS_CODES = (401, 403)


class FyersDepthConnectionError(Exception):
    """
    Raised when a depth websocket connection cannot be established or maintained.
    """


class FyersDepthAuthenticationError(FyersDepthConnectionError):
    """
    Raised when Fyers rejects the credentials themselves rather than the connection.

    Kept apart from a refusal for the same reason the quote feed keeps them apart: a refusal means stop opening connections and keep the ones that worked, while an authentication failure means no connection will ever work and retrying only draws attention to the account.
    """


class FyersDepthConnectionRefusedError(FyersDepthConnectionError):
    """
    Raised when Fyers accepts the credentials but will not serve this connection.

    Carries the evidence that led to the conclusion, so the supervisor can record why it stopped opening connections rather than only that it did.
    """

    def __init__(self, reason, detail):
        """
        Record why a connection was judged refused.

        Args:
            reason (str): A short machine-readable reason, for example "handshake_status_429".
            detail (str): A human-readable description for the log.

        Returns:
            None.
        """
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def discover_websocket_url(authorization):
    """
    Ask Fyers where its tick-by-tick socket is today, falling back to the documented address.

    Fyers publishes one address in its documentation and also serves one from an endpoint, and its own client library asks the endpoint every time. Asking costs one request and covers the case where the two disagree, which is the case the endpoint exists for. Any failure at all falls back to the documented address rather than refusing to connect, because a documented address that might be stale is better than no connection.

    Args:
        authorization (str): The Authorization header value, which is the application identifier and the access token joined by a colon.

    Returns:
        str: The websocket address to connect to.
    """
    try:
        response = requests.get(
            WEBSOCKET_DISCOVERY_URL,
            headers={"Authorization": authorization},
            timeout=DISCOVERY_TIMEOUT_SECONDS,
        )
        payload = response.json()
    except (requests.RequestException, ValueError):
        return WEBSOCKET_ROOT

    for key in ("url", "data", "websocket_url"):
        value = payload.get(key)
        if isinstance(value, str) and value.startswith("wss://"):
            return value
    return WEBSOCKET_ROOT


def subscription_message(symbols, subscribe, channel=DEFAULT_CHANNEL, mode=DEPTH_MODE):
    """
    Build the JSON message that subscribes or unsubscribes a batch of symbols.

    Args:
        symbols (list[str]): Fyers symbol tickers, for example "NSE:NIFTY25MARFUT".
        subscribe (bool): True to subscribe, False to unsubscribe.
        channel (str): The channel to put them on, "1" to "50".
        mode (str): The subscription mode, of which Fyers documents only "depth".

    Returns:
        str: The message to send.
    """
    if subscribe:
        subscription_flag = SUBSCRIBE_FLAG
    else:
        subscription_flag = UNSUBSCRIBE_FLAG
    return json.dumps({
        "type": REQUEST_TYPE_SUBSCRIPTION,
        "data": {
            "subs": subscription_flag,
            "symbols": list(symbols),
            "mode": mode,
            "channel": channel,
        },
    })


def switch_channel_message(resume_channels, pause_channels):
    """
    Build the JSON message that starts and stops the flow on whole channels.

    Args:
        resume_channels (list[str]): Channels to start receiving data on.
        pause_channels (list[str]): Channels to stop receiving data on.

    Returns:
        str: The message to send.
    """
    return json.dumps({
        "type": REQUEST_TYPE_SWITCH_CHANNEL,
        "data": {
            "resumeChannels": list(resume_channels),
            "pauseChannels": list(pause_channels),
        },
    })


class FyersDepthConnection:
    """
    Drives one Fyers tick-by-tick depth websocket connection and keeps it subscribed.

    Attributes:
        symbols (list[str]): The Fyers symbol tickers this connection carries.
        channel (str): The channel they are subscribed on.
        connected (bool): Whether a socket is currently open.
        frames_received (int): Frames read since the object was created, of any kind.
        data_frames_received (int): Frames carrying at least one instrument's depth.
        error_frames_received (int): Frames the server marked as errors.
        bytes_received (int): Total bytes of frames read.
        reconnect_count (int): Times this object has reconnected since it was created.
        last_data_frame_at (float | None): Monotonic time of the most recent data frame, or None if there has not been one.
        last_error_text (str | None): The text of the most recent error frame, kept because it is how Fyers reports a rejected symbol.
    """

    def __init__(self, authorization, symbols, on_frame, channel=DEFAULT_CHANNEL, on_session_start=None, on_error_message=None, logger=None, maximum_reconnect_attempts=None):
        """
        Prepare a connection without opening it.

        Args:
            authorization (str): The Authorization header value, which is the application identifier and the access token joined by a colon.
            symbols (list[str]): The Fyers symbol tickers this connection should carry. Fyers documents a limit of five.
            on_frame (collections.abc.Callable): Called as on_frame(arrival_time_nanoseconds, frame) for every frame. It must not block, because it runs on the socket read path.
            channel (str): The channel to subscribe on, "1" to "50".
            on_session_start (collections.abc.Callable | None): Called with no arguments each time a new session has subscribed, or None to ignore it. This is how the shard learns to discard the book it assembled on the previous session.
            on_error_message (collections.abc.Callable | None): Called as on_error_message(text) for every frame the server marks as an error, or None to ignore them.
            logger (logging.Logger | None): Where to report connection events, or None to stay silent.
            maximum_reconnect_attempts (int | None): Give up after this many consecutive failures, or None to keep trying until stopped. Zero means do not reconnect at all, which is what capacity probing wants.

        Returns:
            None.
        """
        self.authorization = authorization
        self.symbols = list(symbols)
        self.on_frame = on_frame
        self.channel = channel
        self.on_session_start = on_session_start
        self.on_error_message = on_error_message
        self.logger = logger
        self.maximum_reconnect_attempts = maximum_reconnect_attempts

        self.connected = False
        self.frames_received = 0
        self.data_frames_received = 0
        self.error_frames_received = 0
        self.bytes_received = 0
        self.reconnect_count = 0
        self.last_data_frame_at = None
        self.last_error_text = None
        self.connected_at = None
        self.ever_connected = False

    def seconds_since_last_data_frame(self):
        """
        Say how long it has been since a frame carrying actual depth arrived.

        Only frames carrying an instrument refresh the clock, so the error replies never make a silent connection look served. A connection that is subscribed, open, and quiet is the signature of a channel that was never resumed or a symbol the exchange does not serve tick-by-tick data for.

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

    def _handle_frame(self, frame):
        """
        Run the accounting and callbacks for one frame.

        Every frame is handed to on_frame, because the archive stores what came off the socket and the manifest counts only what the packet counter reports. An error frame additionally goes to on_error_message, because a rejected symbol is reported that way and nothing else would surface it.

        Args:
            frame (bytes): The frame as received.

        Returns:
            None.
        """
        arrival_time_nanoseconds = time.time_ns()
        self.frames_received = self.frames_received + 1
        self.bytes_received = self.bytes_received + len(frame)

        error_text = depth_packets.frame_error_text(frame)
        if error_text is not None:
            self.error_frames_received = self.error_frames_received + 1
            self.last_error_text = error_text
            self._log("warning", f"server reported an error: {error_text}")
            if self.on_error_message is not None:
                self.on_error_message(error_text)
        elif depth_packets.frame_packet_count(frame) > 0:
            self.data_frames_received = self.data_frames_received + 1
            self.last_data_frame_at = time.monotonic()

        self.on_frame(arrival_time_nanoseconds, frame)

    async def _send_subscription(self, websocket):
        """
        Subscribe every symbol this connection carries and resume its channel.

        Both messages are needed and the order matters. Subscribing alone puts symbols on a channel that is not flowing, and the resulting silence is indistinguishable from a refused subscription, so this never sends one without the other.

        Args:
            websocket: The open websocket connection to send on.

        Returns:
            None.

        Raises:
            websockets.exceptions.ConnectionClosed: If the connection drops while subscribing.
        """
        await websocket.send(subscription_message(self.symbols, True, self.channel))
        await websocket.send(switch_channel_message([self.channel], []))

    async def _send_keep_alives(self, websocket):
        """
        Send the application level keep-alive every ten seconds until cancelled.

        Args:
            websocket: The open websocket connection to send on.

        Returns:
            None.
        """
        try:
            while True:
                await asyncio.sleep(KEEP_ALIVE_INTERVAL_SECONDS)
                await websocket.send(KEEP_ALIVE_MESSAGE)
        except asyncio.CancelledError:
            return

    async def _run_one_session(self, stop_event):
        """
        Open one connection, subscribe, resume, and read frames until it closes or is stopped.

        Args:
            stop_event (asyncio.Event): Set this to ask the session to close cleanly.

        Returns:
            None.

        Raises:
            FyersDepthAuthenticationError: If Fyers rejected the credentials.
            FyersDepthConnectionRefusedError: If Fyers refused this connection by handshake status or by an early close.
            websockets.exceptions.ConnectionClosed: If an established connection dropped for an ordinary reason.
        """
        url = discover_websocket_url(self.authorization)
        try:
            websocket = await connect(
                url,
                additional_headers={"Authorization": self.authorization},
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
                raise FyersDepthAuthenticationError(
                    f"Fyers rejected the credentials with status {status_code}. The access token is most likely expired or was issued for a different application."
                ) from error
            raise FyersDepthConnectionRefusedError(
                f"handshake_status_{status_code}",
                f"Fyers refused the depth handshake with status {status_code}.",
            ) from error

        self.connected = True
        self.ever_connected = True
        self.connected_at = time.monotonic()
        self._log("info", f"connected to {url}, subscribing {len(self.symbols)} symbols on channel {self.channel}")

        keep_alive_task = asyncio.create_task(self._send_keep_alives(websocket))
        try:
            await self._send_subscription(websocket)
            if self.on_session_start is not None:
                self.on_session_start()

            async for message in websocket:
                frame = message if isinstance(message, bytes) else message.encode("utf-8")
                self._handle_frame(frame)
                if stop_event.is_set():
                    break
        except ConnectionClosed as error:
            open_for = time.monotonic() - self.connected_at
            code = getattr(getattr(error, "rcvd", None), "code", None)
            if open_for < EARLY_CLOSE_SECONDS and code in REFUSAL_CLOSE_CODES:
                raise FyersDepthConnectionRefusedError(
                    f"early_close_{code}",
                    f"Fyers closed the depth connection with code {code} after {open_for:.1f} seconds, which is how it refuses a connection it has already accepted.",
                ) from error
            raise
        finally:
            keep_alive_task.cancel()
            await asyncio.wait({keep_alive_task})
            self.connected = False
            await websocket.close()

    async def run(self, stop_event):
        """
        Keep a connection open until asked to stop, reconnecting with backoff when it drops.

        Every reconnection resubscribes and resumes the channel from scratch, because nothing about the previous session is remembered. It also reports the new session through on_session_start, so the shard discards the book it had assembled: a book half built from one session's snapshot and half from another's differences would be neither.

        Args:
            stop_event (asyncio.Event): Set this to bring the connection down cleanly and return.

        Returns:
            None.

        Raises:
            FyersDepthAuthenticationError: If the credentials were rejected, which no amount of retrying will fix.
            FyersDepthConnectionRefusedError: If Fyers refused the connection, so the caller can record that its limit has been found.
            FyersDepthConnectionError: If the reconnection attempt limit was reached, or the first session failed in probe mode.
        """
        delay = INITIAL_RECONNECT_SECONDS
        consecutive_failures = 0

        while not stop_event.is_set():
            try:
                await self._run_one_session(stop_event)
                consecutive_failures = 0
                delay = INITIAL_RECONNECT_SECONDS
            except (FyersDepthAuthenticationError, FyersDepthConnectionRefusedError):
                raise
            except (ConnectionClosed, OSError, asyncio.TimeoutError) as error:
                consecutive_failures = consecutive_failures + 1
                self._log("warning", f"depth connection lost ({type(error).__name__}: {error}); reconnecting in {delay:.0f}s")
                if self.maximum_reconnect_attempts == 0:
                    raise FyersDepthConnectionError(
                        f"the first session failed ({type(error).__name__}: {error}) and probe mode does not retry."
                    ) from error

            if stop_event.is_set():
                break

            if self.maximum_reconnect_attempts is not None and consecutive_failures > self.maximum_reconnect_attempts:
                raise FyersDepthConnectionError(
                    f"gave up after {consecutive_failures} consecutive reconnection failures."
                )

            self.reconnect_count = self.reconnect_count + 1
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            delay = min(delay * 2, MAXIMUM_RECONNECT_SECONDS)
