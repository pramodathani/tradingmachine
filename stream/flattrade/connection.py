"""
One Flattrade websocket connection, from handshake to reconnection.

This owns a single socket and nothing else, exactly as its Zerodha and Dhan counterparts do. It connects, authenticates, subscribes in one of the two feed modes, hands every market data frame it reads to a callback, and reconnects when the connection drops. It does not decode frames, write them anywhere, or decide which instruments to carry, all of which belong to the shard that drives it.

Three things here are less obvious than they look. The first is that Flattrade authenticates in-band rather than at the handshake: the socket opens with no credentials at all, the client sends a connect message as its first text frame, and the server answers with an `ak` acknowledgement that says OK or Not_Ok, so the handshake status codes the other two brokers classify are kept here only for parity. The second is that the server expects an application level heartbeat, the text message `{"t":"h"}`, every thirty seconds, on top of the protocol pings the websockets library already sends; the protocol pings detect a half-open socket, while the application heartbeat is what keeps Flattrade from closing a healthy one. The third is that Flattrade retains no subscription state across connections, and its own client library has resubscription commented out, so a reconnected socket would sit open and permanently silent unless this class resubscribes on every session, which it does.
"""

import asyncio
import json
import time

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from stream.flattrade import packets

WEBSOCKET_ROOT = "wss://piconnect.flattrade.in/PiConnectWSAPI/"

MODE_TOUCHLINE = "touchline"
MODE_DEPTH = "depth"

TOUCHLINE_SUBSCRIBE_MESSAGE_TYPE = "t"
DEPTH_SUBSCRIBE_MESSAGE_TYPE = "d"
UNSUBSCRIBE_TOUCHLINE_MESSAGE_TYPE = "u"
UNSUBSCRIBE_DEPTH_MESSAGE_TYPE = "ud"

MODE_SUBSCRIBE_MESSAGE_TYPES = {
    MODE_TOUCHLINE: TOUCHLINE_SUBSCRIBE_MESSAGE_TYPE,
    MODE_DEPTH: DEPTH_SUBSCRIBE_MESSAGE_TYPE,
}
MODE_UNSUBSCRIBE_MESSAGE_TYPES = {
    MODE_TOUCHLINE: UNSUBSCRIBE_TOUCHLINE_MESSAGE_TYPE,
    MODE_DEPTH: UNSUBSCRIBE_DEPTH_MESSAGE_TYPE,
}

HEARTBEAT_INTERVAL_SECONDS = 30.0
AUTHENTICATION_ACK_TIMEOUT_SECONDS = 10.0
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


class FlattradeConnectionError(Exception):
    """
    Raised when a websocket connection cannot be established or maintained.
    """


class FlattradeAuthenticationError(FlattradeConnectionError):
    """
    Raised when Flattrade rejects the credentials themselves rather than the connection.

    This is kept apart from a refusal because the responses are opposite. A refusal means the account is at its connection limit and the right move is to stop opening more and carry on with the ones that worked. An authentication failure means the token or user identifier is wrong, no number of connections will work, and retrying is both pointless and the fastest way to draw attention to the account.
    """


class FlattradeConnectionRefusedError(FlattradeConnectionError):
    """
    Raised when Flattrade accepts the credentials but will not serve this connection.

    Carries the evidence that led to the conclusion, so the supervisor can record why it stopped opening connections rather than only that it did. Flattrade documents no refusal signature at all, so the reasons this class knows, a Not_Ok connect acknowledgement on a later session, a handshake status, an early close and an authentication acknowledgement that never arrives, are the complete set of ways it has to say no.
    """

    def __init__(self, reason, detail):
        """
        Record why a connection was judged refused.

        Args:
            reason (str): A short machine-readable reason, for example "connect_not_ok" or "connect_ack_timeout".
            detail (str): A human-readable description for the log.

        Returns:
            None.
        """
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def connect_message(uid, access_token):
    """
    Build the JSON message that authenticates a freshly opened socket.

    Flattrade takes no credentials in the URL, so this is the first message on the wire and the account identifier goes as both `uid` and `actid`, which is how Flattrade's own client sends it.

    Args:
        uid (str): The account identifier the connect acknowledgement expects.
        access_token (str): An access token issued today.

    Returns:
        str: The message to send.
    """
    return json.dumps({
        "ta": "a",
        "uid": uid,
        "actid": uid,
        "source": "API",
        "accesstoken": access_token,
    })


def subscribe_key(instruments):
    """
    Join instruments into the scrip list one message's `k` field carries.

    Flattrade identifies an instrument by exchange and token spelled as one string, and joins several with hashes, so the wire form is also this project's identity form and no translation happens here.

    Args:
        instruments (list[str]): One instrument key per instrument, for example "NSE|22".

    Returns:
        str: The joined key, for example "NSE|22#BSE|508123".
    """
    return "#".join(instruments)


def subscribe_message(mode, instruments):
    """
    Build the JSON message that subscribes a batch of instruments in one feed mode.

    Args:
        mode (str): The feed to subscribe, "touchline" or "depth".
        instruments (list[str]): One instrument key per instrument, for example "NSE|22".

    Returns:
        str: The message to send.

    Raises:
        KeyError: If the mode is not one this module knows.
    """
    return json.dumps({
        "t": MODE_SUBSCRIBE_MESSAGE_TYPES[mode],
        "k": subscribe_key(instruments),
    })


def unsubscribe_message(mode, instruments):
    """
    Build the JSON message that unsubscribes a batch of instruments from one feed mode.

    Args:
        mode (str): The feed to unsubscribe, "touchline" or "depth".
        instruments (list[str]): One instrument key per instrument, for example "NSE|22".

    Returns:
        str: The message to send.

    Raises:
        KeyError: If the mode is not one this module knows.
    """
    return json.dumps({
        "t": MODE_UNSUBSCRIBE_MESSAGE_TYPES[mode],
        "k": subscribe_key(instruments),
    })


def heartbeat_message():
    """
    Build the JSON message that keeps the connection alive.

    Args:
        None.

    Returns:
        str: The message to send.
    """
    return json.dumps({"t": "h"})


class FlattradeConnection:
    """
    Drives one Flattrade websocket connection and keeps it subscribed.

    Attributes:
        instruments (list[str]): The instrument keys this connection carries.
        mode (str): The feed requested for them.
        connected (bool): Whether a socket is currently open.
        frames_received (int): Frames read since the object was created, of any kind.
        data_frames_received (int): Frames carrying touchline or depth messages.
        heartbeats_received (int): Heartbeat acknowledgements read.
        bytes_received (int): Total bytes of frames read.
        text_messages_received (int): Frames that were neither market data nor heartbeat acknowledgements, which are the connect and unsubscribe acknowledgements, order updates and position updates.
        reconnect_count (int): Times this object has reconnected since it was created.
        last_data_frame_at (float | None): Monotonic time of the most recent market data frame, or None if there has not been one.
    """

    def __init__(self, uid, access_token, instruments, on_frame, mode=MODE_TOUCHLINE, on_text=None, logger=None, maximum_reconnect_attempts=None):
        """
        Prepare a connection without opening it.

        Args:
            uid (str): The account identifier the connect message expects.
            access_token (str): An access token issued today.
            instruments (list[str]): The instrument keys this connection should carry, for example "NSE|22".
            on_frame (collections.abc.Callable): Called as on_frame(arrival_time_nanoseconds, frame) for every market data frame. It must not block, because it runs on the socket read path.
            mode (str): The feed to request, "touchline" or "depth".
            on_text (collections.abc.Callable | None): Called as on_text(payload) for every frame that is not market data, or None to ignore them.
            logger (logging.Logger | None): Where to report connection events, or None to stay silent.
            maximum_reconnect_attempts (int | None): Give up after this many consecutive failures, or None to keep trying until stopped. Zero means do not reconnect at all, which is what capacity probing wants, and the first session's failure is raised to the caller rather than silently dropped.

        Returns:
            None.
        """
        self.uid = uid
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
        self.reconnect_count = 0
        self.last_data_frame_at = None
        self.connected_at = None
        self.ever_connected = False

    def seconds_since_last_data_frame(self):
        """
        Say how long it has been since a frame carrying actual data arrived.

        Only touchline and depth messages refresh the clock, so the acknowledgements, the heartbeat acknowledgements and the order and position updates never make a silent connection look served. On an all-text protocol this exclusion is what the whole signal rests on: a connection that is subscribed, open, and quiet apart from heartbeat acknowledgements is the signature of a subscription that was accepted and then quietly not honoured.

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
        Run the accounting for one frame and decide where it belongs.

        Args:
            frame (bytes): The frame as received, encoded to UTF-8.

        Returns:
            dict | None: The parsed message the frame carried, or None when it was not JSON.

        Raises:
            FlattradeAuthenticationError: If the frame was a connect acknowledgement that refused these credentials on the first session ever.
            FlattradeConnectionRefusedError: If the frame was a connect acknowledgement that refused these credentials on a later session while earlier ones worked.
        """
        self.frames_received = self.frames_received + 1
        self.bytes_received = self.bytes_received + len(frame)
        message = packets.parse_message(frame)
        if message is None:
            self.text_messages_received = self.text_messages_received + 1
            return None

        message_type_value = message.get(packets.MESSAGE_TYPE_KEY)
        if message_type_value in packets.MARKET_DATA_MESSAGE_TYPES:
            self.data_frames_received = self.data_frames_received + 1
            self.last_data_frame_at = time.monotonic()
        elif message_type_value == packets.MESSAGE_TYPE_HEARTBEAT_ACK:
            self.heartbeats_received = self.heartbeats_received + 1
        else:
            self.text_messages_received = self.text_messages_received + 1
        return message

    def _handle_frame(self, frame):
        """
        Run the accounting and callbacks for one frame.

        Every frame, whatever it carries, is handed to on_frame encoded to UTF-8, because the archive stores what came off the socket and the manifest counts only the frames whose packet counter reports a packet. Frames that are not market data also go to on_text, so order and position updates reach whoever asked for them without disturbing the market data path.

        Args:
            frame (bytes): The frame as received, encoded to UTF-8.

        Returns:
            None.

        Raises:
            FlattradeAuthenticationError: If the frame was a connect acknowledgement that refused these credentials on the first session ever.
            FlattradeConnectionRefusedError: If the frame was a connect acknowledgement that refused these credentials on a later session while earlier ones worked.
        """
        arrival_time_nanoseconds = time.time_ns()
        message = self._account_frame(frame)
        self.on_frame(arrival_time_nanoseconds, frame)
        if message is not None and message.get(packets.MESSAGE_TYPE_KEY) not in packets.MARKET_DATA_MESSAGE_TYPES and self.on_text is not None:
            self.on_text(message)

    def _raise_for_connect_acknowledgement(self, message):
        """
        Turn a refused connect acknowledgement into the exception the supervisor should see.

        The same Not_Ok acknowledgement means two different things depending on history. On the first session ever the credentials themselves are wrong, which no amount of retrying will fix. On a later session, while earlier ones worked, the credentials are fine and this connection was one too many, which is the only way Flattrade has been observed to refuse a connection.

        Args:
            message (dict): The connect acknowledgement as parsed from the wire.

        Returns:
            None.

        Raises:
            FlattradeAuthenticationError: On the first session ever.
            FlattradeConnectionRefusedError: On any later session.
        """
        if not self.ever_connected:
            raise FlattradeAuthenticationError(
                f"Flattrade refused the connect message with {message.get('s')}: the uid or access token is wrong."
            )
        raise FlattradeConnectionRefusedError(
            "connect_not_ok",
            f"Flattrade answered the connect message with {message.get('s')} on a later session, which is how it refuses a connection.",
        )

    async def _authenticate(self, websocket):
        """
        Send the connect message and wait for the acknowledgement.

        A socket that opens but never answers the connect message is not a working connection, so a missing acknowledgement counts as a refusal rather than as a slow server: the accepted-but-unserved socket is what silence means here.

        Args:
            websocket: The open websocket connection to authenticate on.

        Returns:
            None.

        Raises:
            FlattradeAuthenticationError: If Flattrade refused the credentials on the first session ever.
            FlattradeConnectionRefusedError: If the acknowledgement said Not_Ok on a later session, or never arrived within the timeout.
            websockets.exceptions.ConnectionClosed: If the connection drops while authenticating.
        """
        await websocket.send(connect_message(self.uid, self.access_token))
        deadline = time.monotonic() + AUTHENTICATION_ACK_TIMEOUT_SECONDS
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise FlattradeConnectionRefusedError(
                    "connect_ack_timeout",
                    f"Flattrade sent no connect acknowledgement within {AUTHENTICATION_ACK_TIMEOUT_SECONDS:.0f} seconds.",
                )
            message = await asyncio.wait_for(websocket.recv(), timeout=remaining)
            frame = message.encode("utf-8")
            parsed = self._account_frame(frame)
            if parsed is None:
                continue
            if parsed.get(packets.MESSAGE_TYPE_KEY) == packets.MESSAGE_TYPE_AUTHENTICATION_ACK:
                if parsed.get("s") != "OK":
                    self._raise_for_connect_acknowledgement(parsed)
                return
            if self.on_text is not None:
                self.on_text(parsed)

    async def _send_subscription(self, websocket):
        """
        Subscribe every instrument this connection carries, in the requested mode.

        Instruments are sent in batches of one hundred, a choice rather than a documented rule, and the first live run checks that one acknowledgement comes back per scrip. Flattrade retains no subscription state across connections, so this runs on every connection including reconnections.

        Args:
            websocket: The open websocket connection to send on.

        Returns:
            None.

        Raises:
            websockets.exceptions.ConnectionClosed: If the connection drops while subscribing.
        """
        for start in range(0, len(self.instruments), SUBSCRIBE_BATCH_SIZE):
            batch = self.instruments[start:start + SUBSCRIBE_BATCH_SIZE]
            await websocket.send(subscribe_message(self.mode, batch))

    async def _send_heartbeats(self, websocket):
        """
        Send the application level heartbeat every thirty seconds until cancelled.

        Args:
            websocket: The open websocket connection to send on.

        Returns:
            None.
        """
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
                await websocket.send(heartbeat_message())
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
            FlattradeAuthenticationError: If Flattrade rejected the credentials.
            FlattradeConnectionRefusedError: If Flattrade refused this connection, whether by connect acknowledgement, by handshake status, by an early close, or by never acknowledging.
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
                raise FlattradeAuthenticationError(
                    f"Flattrade rejected the credentials with status {status_code}. The access token is most likely expired or was issued for a different account."
                ) from error
            raise FlattradeConnectionRefusedError(
                f"handshake_status_{status_code}",
                f"Flattrade refused the handshake with status {status_code}.",
            ) from error

        self.connected = True
        self.ever_connected = True
        self.connected_at = time.monotonic()
        self._log("info", f"connected, subscribing {len(self.instruments)} instruments in {self.mode} mode")

        heartbeat_task = asyncio.create_task(self._send_heartbeats(websocket))
        try:
            await self._authenticate(websocket)
            await self._send_subscription(websocket)
            async for message in websocket:
                self._handle_frame(message.encode("utf-8"))
                if stop_event.is_set():
                    break
        except ConnectionClosed as error:
            open_for = time.monotonic() - self.connected_at
            code = getattr(getattr(error, "rcvd", None), "code", None)
            if open_for < EARLY_CLOSE_SECONDS and code in REFUSAL_CLOSE_CODES:
                raise FlattradeConnectionRefusedError(
                    f"early_close_{code}",
                    f"Flattrade closed the connection with code {code} after {open_for:.1f} seconds, which is how it refuses a connection it has already accepted.",
                ) from error
            raise
        finally:
            heartbeat_task.cancel()
            await asyncio.wait({heartbeat_task})
            self.connected = False
            await websocket.close()

    async def run(self, stop_event):
        """
        Keep a connection open until asked to stop, reconnecting with backoff when it drops.

        Every reconnection authenticates and resubscribes from scratch, because Flattrade remembers no subscription state across connections and a reconnected socket would otherwise stay open and permanently silent.

        The backoff starts at two seconds and doubles to a minute. Flattrade documents no refusal signature, so a connection that keeps being refused should stop the supervisor from opening further connections rather than be retried.

        Args:
            stop_event (asyncio.Event): Set this to bring the connection down cleanly and return.

        Returns:
            None.

        Raises:
            FlattradeAuthenticationError: If the credentials were rejected, which no amount of retrying will fix.
            FlattradeConnectionRefusedError: If Flattrade refused the connection, so the caller can record that its limit has been found.
            FlattradeConnectionError: If the reconnection attempt limit was reached, or the first session failed in probe mode.
        """
        delay = INITIAL_RECONNECT_SECONDS
        consecutive_failures = 0

        while not stop_event.is_set():
            try:
                await self._run_one_session(stop_event)
                consecutive_failures = 0
                delay = INITIAL_RECONNECT_SECONDS
            except (FlattradeAuthenticationError, FlattradeConnectionRefusedError):
                raise
            except (ConnectionClosed, OSError, asyncio.TimeoutError) as error:
                consecutive_failures = consecutive_failures + 1
                self._log("warning", f"connection lost ({type(error).__name__}: {error}); reconnecting in {delay:.0f}s")
                if self.maximum_reconnect_attempts == 0:
                    raise FlattradeConnectionError(
                        f"the first session failed ({type(error).__name__}: {error}) and probe mode does not retry."
                    ) from error

            if stop_event.is_set():
                break

            if self.maximum_reconnect_attempts is not None and consecutive_failures > self.maximum_reconnect_attempts:
                raise FlattradeConnectionError(
                    f"gave up after {consecutive_failures} consecutive reconnection failures."
                )

            self.reconnect_count = self.reconnect_count + 1
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            delay = min(delay * 2, MAXIMUM_RECONNECT_SECONDS)