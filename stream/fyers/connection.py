"""
One Fyers quote websocket connection, from handshake to reconnection.

This owns a single socket and nothing else, exactly as its Zerodha, Dhan, Flattrade and Shoonya counterparts do. It connects, authenticates, sets the feed mode, subscribes, hands every frame it reads to a callback, and reconnects when the connection drops. It does not decode frames, write them anywhere, or decide which instruments to carry, all of which belong to the shard that drives it.

Four things here are less obvious than they look.

The first is that Fyers authenticates in-band and with the wrong-looking token. The socket opens with no headers at all, the client sends a binary authentication message as its first frame, and the token that message carries is not the access token but the `hsm_key` claim decoded out of it. The handshake status codes the other brokers classify are kept here only for parity.

The second is that the server sets the pace of an obligation it never mentions again. Its authentication reply carries an acknowledgement interval, and the client must send an acknowledgement quoting the last message number every that-many data frames. A connection that stops acknowledging is eventually stopped being fed, which looks exactly like a subscription that was quietly dropped.

The third is that the feed mode is a separate message. A socket that has authenticated but has not been told full or lite has been told nothing, and subscribing before the mode is set is how a connection ends up delivering a single price per instrument when it was meant to deliver twenty.

The fourth is that Fyers retains no subscription state across connections and renumbers its topics per connection, so a reconnected socket must resubscribe from scratch and must throw away the topic table it learned. The topic table lives in the assembler the shard holds, so this class reports a new session through `on_session_start` rather than reaching into it.
"""

import asyncio
import struct
import time

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from stream.fyers import packets

WEBSOCKET_ROOT = "wss://socket.fyers.in/hsm/v1-5/prod"

SOURCE_NAME = "tradingmachine"
AUTHENTICATION_MODE = "P"

REQUEST_TYPE_AUTHENTICATION = 1
REQUEST_TYPE_ACKNOWLEDGEMENT = 3
REQUEST_TYPE_SUBSCRIBE = 4
REQUEST_TYPE_UNSUBSCRIBE = 5
REQUEST_TYPE_MODE = 12

MODE_FULL = "full"
MODE_LITE = "lite"

MODE_BYTES = {
    MODE_FULL: 70,
    MODE_LITE: 76,
}

DEFAULT_CHANNEL_NUMBER = 11

AUTHENTICATION_SUCCESS_VALUE = "K"
KEEP_ALIVE_FRAME = bytes([0, 1, 11])
KEEP_ALIVE_INTERVAL_SECONDS = 10.0

AUTHENTICATION_ACK_TIMEOUT_SECONDS = 15.0
SUBSCRIBE_BATCH_SIZE = 500
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


class FyersConnectionError(Exception):
    """
    Raised when a websocket connection cannot be established or maintained.
    """


class FyersAuthenticationError(FyersConnectionError):
    """
    Raised when Fyers rejects the credentials themselves rather than the connection.

    This is kept apart from a refusal because the responses are opposite. A refusal means the account is at its connection limit and the right move is to stop opening more and carry on with the ones that worked. An authentication failure means the token is wrong or expired, no number of connections will work, and retrying is both pointless and the fastest way to draw attention to the account.
    """


class FyersConnectionRefusedError(FyersConnectionError):
    """
    Raised when Fyers accepts the credentials but will not serve this connection.

    Carries the evidence that led to the conclusion, so the supervisor can record why it stopped opening connections rather than only that it did. Fyers documents one connection per user and nothing about how a second is refused, so the reasons this class knows, a failed authentication reply on a later session, a handshake status, an early close and an authentication reply that never arrives, are the complete set of ways it has been observed to say no.
    """

    def __init__(self, reason, detail):
        """
        Record why a connection was judged refused.

        Args:
            reason (str): A short machine-readable reason, for example "authentication_not_ok" or "authentication_ack_timeout".
            detail (str): A human-readable description for the log.

        Returns:
            None.
        """
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def build_request(request_type, fields):
    """
    Wrap a request's fields in the framing every message on this socket shares.

    Every frame in both directions is a two byte length, a one byte type, a one byte field count, and then each field as a one byte identifier, a two byte length and its payload. The length counts everything after itself.

    Args:
        request_type (int): The request type, for example 4 for a subscription.
        fields (list[tuple]): One (field_identifier, payload_bytes) pair per field, in wire order.

    Returns:
        bytes: The complete message, ready to send as a binary frame.
    """
    body = bytearray()
    body.append(request_type)
    body.append(len(fields))
    for field_identifier, payload in fields:
        body.append(field_identifier)
        body.extend(struct.pack(">H", len(payload)))
        body.extend(payload)

    message = bytearray()
    message.extend(struct.pack(">H", len(body)))
    message.extend(body)
    return bytes(message)


def authentication_message(hsm_key):
    """
    Build the binary message that authenticates a freshly opened socket.

    The token here is the `hsm_key` claim carried inside the access token, not the access token itself, which is the single most surprising thing about this protocol and the one most likely to be got wrong when reading the field name alone.

    Args:
        hsm_key (str): The hsm_key claim decoded out of today's access token.

    Returns:
        bytes: The message to send.
    """
    return build_request(
        REQUEST_TYPE_AUTHENTICATION,
        [
            (1, hsm_key.encode("utf-8")),
            (2, AUTHENTICATION_MODE.encode("utf-8")),
            (3, bytes([1])),
            (4, SOURCE_NAME.encode("utf-8")),
        ],
    )


def mode_message(mode, channel_number=DEFAULT_CHANNEL_NUMBER):
    """
    Build the message that tells the server how much of each instrument to send.

    The channel field is a sixty four bit mask rather than a channel number, so the channel this connection uses is set by raising the bit at its position.

    Args:
        mode (str): The feed mode, "full" for every field or "lite" for the last price only.
        channel_number (int): Which channel the mode applies to.

    Returns:
        bytes: The message to send.

    Raises:
        KeyError: If the mode is not one this module knows.
    """
    channel_bits = 1 << channel_number
    return build_request(
        REQUEST_TYPE_MODE,
        [
            (1, struct.pack(">Q", channel_bits)),
            (2, bytes([MODE_BYTES[mode]])),
        ],
    )


def scrip_list_payload(instruments):
    """
    Pack a batch of subscription keys into the field a subscription message carries.

    The count is two bytes and each key is introduced by a single byte of its own length, so a key longer than two hundred and fifty five bytes cannot be expressed. No Fyers key comes close.

    Args:
        instruments (list[str]): One subscription key per instrument, for example "sf|nse_cm|2885".

    Returns:
        bytes: The packed list.
    """
    payload = bytearray()
    payload.extend(struct.pack(">H", len(instruments)))
    for instrument in instruments:
        encoded = str(instrument).encode("ascii")
        payload.append(len(encoded))
        payload.extend(encoded)
    return bytes(payload)


def subscribe_message(instruments, channel_number=DEFAULT_CHANNEL_NUMBER):
    """
    Build the message that subscribes a batch of instruments.

    Args:
        instruments (list[str]): One subscription key per instrument, for example "sf|nse_cm|2885".
        channel_number (int): Which channel to subscribe them on.

    Returns:
        bytes: The message to send.
    """
    return build_request(
        REQUEST_TYPE_SUBSCRIBE,
        [
            (1, scrip_list_payload(instruments)),
            (2, bytes([channel_number])),
        ],
    )


def unsubscribe_message(instruments, channel_number=DEFAULT_CHANNEL_NUMBER):
    """
    Build the message that unsubscribes a batch of instruments.

    Args:
        instruments (list[str]): One subscription key per instrument, for example "sf|nse_cm|2885".
        channel_number (int): Which channel to unsubscribe them from.

    Returns:
        bytes: The message to send.
    """
    return build_request(
        REQUEST_TYPE_UNSUBSCRIBE,
        [
            (1, scrip_list_payload(instruments)),
            (2, bytes([channel_number])),
        ],
    )


def acknowledgement_message(message_number):
    """
    Build the message that acknowledges everything received up to one message number.

    Args:
        message_number (int): The message number from the most recent data frame.

    Returns:
        bytes: The message to send.
    """
    return build_request(
        REQUEST_TYPE_ACKNOWLEDGEMENT,
        [
            (1, struct.pack(">I", message_number)),
        ],
    )


def read_authentication_reply(frame):
    """
    Read the status and the acknowledgement interval out of an authentication reply.

    Args:
        frame (bytes): One complete websocket frame as received.

    Returns:
        tuple: A (status, acknowledgement_interval) pair. The status is the single character the server sent, "K" when the credentials were accepted, or None when the frame is not a readable authentication reply. The interval is None when the frame did not carry one.
    """
    if packets.frame_response_type(frame) != packets.RESPONSE_TYPE_AUTHENTICATION:
        return (None, None)

    offset = 5
    if offset + 2 > len(frame):
        return (None, None)
    field_length = struct.unpack_from(">H", frame, offset)[0]
    offset = offset + 2
    if offset + field_length > len(frame):
        return (None, None)
    status = frame[offset:offset + field_length].decode("utf-8", errors="ignore")
    offset = offset + field_length

    acknowledgement_interval = None
    offset = offset + 1
    if offset + 2 <= len(frame):
        field_length = struct.unpack_from(">H", frame, offset)[0]
        offset = offset + 2
        if field_length == 4 and offset + 4 <= len(frame):
            acknowledgement_interval = struct.unpack_from(">I", frame, offset)[0]

    return (status, acknowledgement_interval)


class FyersConnection:
    """
    Drives one Fyers quote websocket connection and keeps it subscribed.

    Attributes:
        instruments (list[str]): The subscription keys this connection carries.
        mode (str): The feed mode requested for them.
        connected (bool): Whether a socket is currently open.
        frames_received (int): Frames read since the object was created, of any kind.
        data_frames_received (int): Frames carrying market data.
        control_frames_received (int): Frames that were not market data, which are the authentication, subscription, mode and channel replies.
        bytes_received (int): Total bytes of frames read.
        acknowledgements_sent (int): Acknowledgement messages sent since the object was created.
        acknowledgement_interval (int | None): How many data frames the server asked to be acknowledged at a time, from its authentication reply.
        reconnect_count (int): Times this object has reconnected since it was created.
        last_data_frame_at (float | None): Monotonic time of the most recent market data frame, or None if there has not been one.
    """

    def __init__(self, hsm_key, instruments, on_frame, mode=MODE_FULL, on_session_start=None, on_control=None, logger=None, maximum_reconnect_attempts=None, channel_number=DEFAULT_CHANNEL_NUMBER):
        """
        Prepare a connection without opening it.

        Args:
            hsm_key (str): The hsm_key claim decoded out of today's access token.
            instruments (list[str]): The subscription keys this connection should carry, for example "sf|nse_cm|2885".
            on_frame (collections.abc.Callable): Called as on_frame(arrival_time_nanoseconds, frame) for every frame. It must not block, because it runs on the socket read path.
            mode (str): The feed mode to request, "full" or "lite".
            on_session_start (collections.abc.Callable | None): Called with no arguments each time a new session has authenticated, before anything is subscribed, or None to ignore it. This is how the shard learns to discard the topic table from the previous session.
            on_control (collections.abc.Callable | None): Called as on_control(response_type, frame) for every frame that is not market data, or None to ignore them.
            logger (logging.Logger | None): Where to report connection events, or None to stay silent.
            maximum_reconnect_attempts (int | None): Give up after this many consecutive failures, or None to keep trying until stopped. Zero means do not reconnect at all, which is what capacity probing wants, and the first session's failure is raised to the caller rather than silently dropped.
            channel_number (int): Which channel to subscribe on.

        Returns:
            None.
        """
        self.hsm_key = hsm_key
        self.instruments = list(instruments)
        self.on_frame = on_frame
        self.mode = mode
        self.on_session_start = on_session_start
        self.on_control = on_control
        self.logger = logger
        self.maximum_reconnect_attempts = maximum_reconnect_attempts
        self.channel_number = channel_number

        self.connected = False
        self.frames_received = 0
        self.data_frames_received = 0
        self.control_frames_received = 0
        self.bytes_received = 0
        self.acknowledgements_sent = 0
        self.acknowledgement_interval = None
        self.reconnect_count = 0
        self.last_data_frame_at = None
        self.connected_at = None
        self.ever_connected = False

        self.frames_since_acknowledgement = 0
        self.last_message_number = None

    def seconds_since_last_data_frame(self):
        """
        Say how long it has been since a frame carrying actual data arrived.

        Only market data frames refresh the clock, so the authentication, subscription and mode replies never make a silent connection look served. A connection that is subscribed, open, and quiet apart from its replies is the signature of a subscription that was accepted and then quietly not honoured, which on this broker is also what a wrong index name produces.

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

    def _account_frame(self, frame):
        """
        Run the accounting for one frame and say what kind it was.

        Args:
            frame (bytes): The frame as received.

        Returns:
            int | None: The frame's response type, or None when it was too short to carry one.
        """
        self.frames_received = self.frames_received + 1
        self.bytes_received = self.bytes_received + len(frame)

        response_type = packets.frame_response_type(frame)
        if response_type == packets.RESPONSE_TYPE_DATA_FEED:
            self.data_frames_received = self.data_frames_received + 1
            self.last_data_frame_at = time.monotonic()
            self.frames_since_acknowledgement = self.frames_since_acknowledgement + 1
            message_number = packets.frame_message_number(frame)
            if message_number is not None:
                self.last_message_number = message_number
        else:
            self.control_frames_received = self.control_frames_received + 1
        return response_type

    def _acknowledgement_due(self):
        """
        Say whether enough data frames have arrived to owe the server an acknowledgement.

        Returns:
            bool: True when an acknowledgement should be sent now.
        """
        if not self.acknowledgement_interval:
            return False
        if self.last_message_number is None:
            return False
        return self.frames_since_acknowledgement >= self.acknowledgement_interval

    async def _send_acknowledgement(self, websocket):
        """
        Acknowledge everything received so far and reset the count.

        Args:
            websocket: The open websocket connection to send on.

        Returns:
            None.

        Raises:
            websockets.exceptions.ConnectionClosed: If the connection drops while sending.
        """
        await websocket.send(acknowledgement_message(self.last_message_number))
        self.acknowledgements_sent = self.acknowledgements_sent + 1
        self.frames_since_acknowledgement = 0

    def _handle_frame(self, frame, response_type):
        """
        Run the callbacks for one frame.

        Every frame, whatever it carries, is handed to on_frame, because the archive stores what came off the socket and the manifest counts only the frames whose packet counter reports a packet. Frames that are not market data also go to on_control, so the subscription and mode replies reach whoever asked for them without disturbing the market data path.

        Args:
            frame (bytes): The frame as received.
            response_type (int | None): The frame's response type, from the accounting.

        Returns:
            None.
        """
        arrival_time_nanoseconds = time.time_ns()
        self.on_frame(arrival_time_nanoseconds, frame)
        if response_type != packets.RESPONSE_TYPE_DATA_FEED and self.on_control is not None:
            self.on_control(response_type, frame)

    async def _authenticate(self, websocket):
        """
        Send the authentication message and wait for the reply.

        A socket that opens but never answers is not a working connection, so a missing reply counts as a refusal rather than as a slow server: an accepted-but-unserved socket is what silence means here.

        Args:
            websocket: The open websocket connection to authenticate on.

        Returns:
            None.

        Raises:
            FyersAuthenticationError: If Fyers refused the credentials on the first session ever.
            FyersConnectionRefusedError: If the reply refused this connection on a later session, or never arrived within the timeout.
            websockets.exceptions.ConnectionClosed: If the connection drops while authenticating.
        """
        await websocket.send(authentication_message(self.hsm_key))
        deadline = time.monotonic() + AUTHENTICATION_ACK_TIMEOUT_SECONDS

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise FyersConnectionRefusedError(
                    "authentication_ack_timeout",
                    f"Fyers sent no authentication reply within {AUTHENTICATION_ACK_TIMEOUT_SECONDS:.0f} seconds.",
                )

            message = await asyncio.wait_for(websocket.recv(), timeout=remaining)
            frame = message if isinstance(message, bytes) else message.encode("utf-8")
            response_type = self._account_frame(frame)
            self._handle_frame(frame, response_type)

            if response_type != packets.RESPONSE_TYPE_AUTHENTICATION:
                continue

            status, acknowledgement_interval = read_authentication_reply(frame)
            if status != AUTHENTICATION_SUCCESS_VALUE:
                self._raise_for_authentication_reply(status)
            self.acknowledgement_interval = acknowledgement_interval
            self._log("info", f"authenticated, acknowledging every {acknowledgement_interval} data frames")
            return

    def _raise_for_authentication_reply(self, status):
        """
        Turn a refused authentication reply into the exception the supervisor should see.

        The same refusal means two different things depending on history. On the first session ever the token itself is wrong or expired, which no amount of retrying will fix. On a later session, while earlier ones worked, the token is fine and this connection was one too many, which is how Fyers refuses a connection it has no room for.

        Args:
            status (str | None): The status character the server sent, or None when the reply was unreadable.

        Returns:
            None.

        Raises:
            FyersAuthenticationError: On the first session ever.
            FyersConnectionRefusedError: On any later session.
        """
        if not self.ever_connected:
            raise FyersAuthenticationError(
                f"Fyers refused the authentication message with {status!r}: the access token is most likely expired or its hsm_key is wrong."
            )
        raise FyersConnectionRefusedError(
            "authentication_not_ok",
            f"Fyers answered the authentication message with {status!r} on a later session, which is how it refuses a connection it has no room for.",
        )

    async def _send_subscription(self, websocket):
        """
        Set the feed mode and subscribe every instrument this connection carries.

        The mode goes first because a socket that has authenticated but has not been told full or lite has been told nothing, and a subscription sent before it can be served in the wrong shape.

        Instruments are sent in batches, a choice rather than a documented rule, and the capacity probe is what establishes whether a whole batch is honoured. Fyers retains no subscription state across connections, so this runs on every session including reconnections.

        Args:
            websocket: The open websocket connection to send on.

        Returns:
            None.

        Raises:
            websockets.exceptions.ConnectionClosed: If the connection drops while subscribing.
        """
        await websocket.send(mode_message(self.mode, self.channel_number))
        for start in range(0, len(self.instruments), SUBSCRIBE_BATCH_SIZE):
            batch = self.instruments[start:start + SUBSCRIBE_BATCH_SIZE]
            await websocket.send(subscribe_message(batch, self.channel_number))

    async def _send_keep_alives(self, websocket):
        """
        Send the application level keep-alive every ten seconds until cancelled.

        The protocol pings the websockets library sends detect a half-open socket. This is what keeps Fyers from closing a healthy one, which is a different job, so both run.

        Args:
            websocket: The open websocket connection to send on.

        Returns:
            None.
        """
        try:
            while True:
                await asyncio.sleep(KEEP_ALIVE_INTERVAL_SECONDS)
                await websocket.send(KEEP_ALIVE_FRAME)
        except asyncio.CancelledError:
            return

    async def _run_one_session(self, stop_event):
        """
        Open one connection, authenticate, subscribe, and read frames until it closes or is stopped.

        Args:
            stop_event (asyncio.Event): Set this to ask the session to close cleanly.

        Returns:
            None.

        Raises:
            FyersAuthenticationError: If Fyers rejected the credentials.
            FyersConnectionRefusedError: If Fyers refused this connection, whether by authentication reply, by handshake status, by an early close, or by never replying.
            websockets.exceptions.ConnectionClosed: If an established connection dropped for an ordinary reason.
        """
        try:
            websocket = await connect(
                WEBSOCKET_ROOT,
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
                raise FyersAuthenticationError(
                    f"Fyers rejected the credentials with status {status_code}. The access token is most likely expired or was issued for a different application."
                ) from error
            raise FyersConnectionRefusedError(
                f"handshake_status_{status_code}",
                f"Fyers refused the handshake with status {status_code}.",
            ) from error

        self.connected = True
        self.ever_connected = True
        self.connected_at = time.monotonic()
        self.frames_since_acknowledgement = 0
        self.last_message_number = None
        self._log("info", f"connected, subscribing {len(self.instruments)} instruments in {self.mode} mode")

        keep_alive_task = asyncio.create_task(self._send_keep_alives(websocket))
        try:
            await self._authenticate(websocket)
            if self.on_session_start is not None:
                self.on_session_start()
            await self._send_subscription(websocket)

            async for message in websocket:
                frame = message if isinstance(message, bytes) else message.encode("utf-8")
                response_type = self._account_frame(frame)
                self._handle_frame(frame, response_type)
                if self._acknowledgement_due():
                    await self._send_acknowledgement(websocket)
                if stop_event.is_set():
                    break
        except ConnectionClosed as error:
            open_for = time.monotonic() - self.connected_at
            code = getattr(getattr(error, "rcvd", None), "code", None)
            if open_for < EARLY_CLOSE_SECONDS and code in REFUSAL_CLOSE_CODES:
                raise FyersConnectionRefusedError(
                    f"early_close_{code}",
                    f"Fyers closed the connection with code {code} after {open_for:.1f} seconds, which is how it refuses a connection it has already accepted.",
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

        Every reconnection authenticates, sets the mode and resubscribes from scratch, because Fyers remembers no subscription state across connections and a reconnected socket would otherwise stay open and permanently silent. It also reports the new session through on_session_start, because Fyers renumbers its topics per connection and a topic table carried across a reconnection would name the wrong instruments.

        The backoff starts at two seconds and doubles to a minute. Fyers documents one connection per user, so a connection that is refused should stop the supervisor from opening further connections rather than be retried.

        Args:
            stop_event (asyncio.Event): Set this to bring the connection down cleanly and return.

        Returns:
            None.

        Raises:
            FyersAuthenticationError: If the credentials were rejected, which no amount of retrying will fix.
            FyersConnectionRefusedError: If Fyers refused the connection, so the caller can record that its limit has been found.
            FyersConnectionError: If the reconnection attempt limit was reached, or the first session failed in probe mode.
        """
        delay = INITIAL_RECONNECT_SECONDS
        consecutive_failures = 0

        while not stop_event.is_set():
            try:
                await self._run_one_session(stop_event)
                consecutive_failures = 0
                delay = INITIAL_RECONNECT_SECONDS
            except (FyersAuthenticationError, FyersConnectionRefusedError):
                raise
            except (ConnectionClosed, OSError, asyncio.TimeoutError) as error:
                consecutive_failures = consecutive_failures + 1
                self._log("warning", f"connection lost ({type(error).__name__}: {error}); reconnecting in {delay:.0f}s")
                if self.maximum_reconnect_attempts == 0:
                    raise FyersConnectionError(
                        f"the first session failed ({type(error).__name__}: {error}) and probe mode does not retry."
                    ) from error

            if stop_event.is_set():
                break

            if self.maximum_reconnect_attempts is not None and consecutive_failures > self.maximum_reconnect_attempts:
                raise FyersConnectionError(
                    f"gave up after {consecutive_failures} consecutive reconnection failures."
                )

            self.reconnect_count = self.reconnect_count + 1
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            delay = min(delay * 2, MAXIMUM_RECONNECT_SECONDS)
