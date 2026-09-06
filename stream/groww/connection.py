"""
One Groww market data connection, from handshake to reconnection.

Groww's feed is the one transport here that is not a plain websocket protocol. It is a NATS message bus carried over a websocket: the websocket carries the NATS protocol's text operations and, for market data, length delimited protobuf payloads. This module hand-rolls the handful of NATS operations the feed needs rather than taking the nats-py client, for the same reasons the other brokers' connections hand-roll their own protocols: it keeps Groww structurally identical to its five counterparts, keeps our own reconnection and backoff, and keeps the refusal classification the capacity probe depends on. The CONNECT shape and the signature encoding were read out of nats-py's source and the NATS server's authentication code rather than guessed.

This class owns a single socket and nothing else, exactly as every other broker's connection does. It connects, authenticates, subscribes, hands every complete NATS message to a callback, and reconnects when the connection drops. It does not decode payloads, write them anywhere, or decide which subjects to carry.

Four things here are less obvious than they look.

The first is that the credential that opens the websocket is not what authenticates the NATS session. The websocket opens with no headers at all. The server answers with an INFO operation carrying a fresh nonce, and the client answers with CONNECT carrying the socket token as a JSON Web Token and an Ed25519 signature over that nonce, made with the seed whose public half minted the token. The nonce is fresh per connection, so the signature is made per session and never reused.

The second is that the byte stream is not the record. One websocket frame may hold half a NATS message, several of them, or the tail of one and the head of the next, and a protobuf payload can itself contain the carriage return and newline that ends a control line. The declared payload length in each MSG header is the only safe boundary, and the ProtocolReader in this module is what honours it. It hands the callback the whole NATS message operation, header line included, because the subject is the only place the instrument's exchange token appears.

The third is that there are two keep-alive layers and they do different jobs. The websockets library answers the websocket's own pings, which detects a half-open socket. Separately this connection sends a NATS PING every sixty seconds and answers the server's NATS PINGs with PONGs, which is what keeps a healthy socket from being closed by the bus for silence, and it matches the sixty second interval Groww's own SDK uses.

The fourth is that NATS retains no subscription state across connections, so a reconnected socket resubscribes from scratch on every session.
"""

import asyncio
import json
import time

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from stream.groww import credentials, packets

WEBSOCKET_URL = "wss://socket-api.groww.in"

CONNECT_NAME = "tradingmachine"
CONNECT_LANG = "python"
CONNECT_VERSION = "1.0"
CONNECT_PROTOCOL = 1

SUBSCRIBE_BATCH_SIZE = 500

NATS_PING_INTERVAL_SECONDS = 60.0

HANDSHAKE_TIMEOUT_SECONDS = 15.0

WEBSOCKET_PING_INTERVAL_SECONDS = 20.0
WEBSOCKET_PING_TIMEOUT_SECONDS = 10.0
OPEN_TIMEOUT_SECONDS = 30.0
CLOSE_TIMEOUT_SECONDS = 5.0
MAXIMUM_FRAME_BYTES = 16 * 1024 * 1024
MAXIMUM_MESSAGE_BYTES = 16 * 1024 * 1024

INITIAL_RECONNECT_SECONDS = 2.0
MAXIMUM_RECONNECT_SECONDS = 60.0
EARLY_CLOSE_SECONDS = 10.0

REFUSAL_CLOSE_CODES = (1008, 1011, 1013)
AUTHENTICATION_STATUS_CODES = (401, 403)

PROTOCOL_MESSAGE_KIND = "message"
PROTOCOL_OPERATION_KIND = "operation"


class GrowwConnectionError(Exception):
    """
    Raised when a websocket connection cannot be established or maintained.
    """


class GrowwAuthenticationError(GrowwConnectionError):
    """
    Raised when Groww rejects the credentials themselves rather than the connection.

    This is kept apart from a refusal because the responses are opposite. A refusal means the account is at its connection or subscription limit and the right move is to stop opening more and carry on with the ones that worked. An authorization violation means the socket token or its key is wrong, no number of connections will work, and retrying is both pointless and the fastest way to draw attention to the account.
    """


class GrowwConnectionRefusedError(GrowwConnectionError):
    """
    Raised when Groww accepts the credentials but will not serve this connection.

    Carries the evidence that led to the conclusion, so the supervisor can record why it stopped opening connections rather than only that it did. Groww documents a thousand instruments at a time and nothing about how it says no beyond that, so the reasons this class knows are an error naming a maximum, an authorization violation on a session that follows ones which worked, and a handshake status.
    """

    def __init__(self, reason, detail):
        """
        Record why a connection was judged refused.

        Args:
            reason (str): A short machine-readable reason, for example "maximum_reached" or "handshake_pong_timeout".
            detail (str): A human-readable description for the log.

        Returns:
            None.
        """
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class ProtocolReader:
    """
    Split the NATS byte stream arriving on the websocket into protocol operations.

    The websocket delivers bytes without regard to where one NATS operation ends and the next begins. This reader accumulates them and yields one item per complete operation: the operation line itself for every control operation, and the whole message operation, header line, payload and trailing line terminator included, for every MSG. The declared payload length is the only boundary honoured, because a protobuf payload can contain the same two bytes that end a control line.

    Attributes:
        buffer (bytes): Bytes received but not yet split into operations.
        pending_header (bytes | None): The header line of a message whose payload is still arriving.
        pending_bytes (int): How many payload bytes of that message are still missing.
    """

    def __init__(self):
        """
        Prepare an empty reader.

        Returns:
            None.
        """
        self.buffer = b""
        self.pending_header = None
        self.pending_bytes = 0

    def feed(self, data):
        """
        Consume newly received bytes and yield every operation they complete.

        Args:
            data (bytes): The bytes of one websocket frame, which may hold any fragment of any number of operations.

        Yields:
            tuple: A (kind, content) pair per completed operation, where kind is PROTOCOL_MESSAGE_KIND and content is the whole message operation for a MSG, or kind is PROTOCOL_OPERATION_KIND and content is the operation line without its terminator for anything else.

        Raises:
            GrowwConnectionError: If a message header cannot be read or declares a payload beyond any plausible size, because the stream can then no longer be split safely and the connection must be rebuilt.
        """
        self.buffer = self.buffer + data

        while True:
            if self.pending_header is None:
                terminator = self.buffer.find(packets.LINE_TERMINATOR)
                if terminator < 0:
                    return

                line = self.buffer[:terminator]
                self.buffer = self.buffer[terminator + len(packets.LINE_TERMINATOR):]

                parts = line.split()
                if not parts:
                    continue

                if parts[0] == packets.MESSAGE_OPERATION:
                    try:
                        declared = int(parts[-1])
                    except ValueError:
                        raise GrowwConnectionError(
                            f"unreadable message header {line!r}; resynchronising by reconnecting."
                        )
                    if declared < 0 or declared > MAXIMUM_MESSAGE_BYTES:
                        raise GrowwConnectionError(
                            f"message header {line!r} declares {declared} payload bytes, beyond any plausible size; resynchronising by rebuilding the connection."
                        )
                    self.pending_header = line
                    self.pending_bytes = declared
                    continue

                yield (PROTOCOL_OPERATION_KIND, line)
                continue

            if len(self.buffer) < self.pending_bytes + len(packets.LINE_TERMINATOR):
                return

            whole = self.pending_header + packets.LINE_TERMINATOR
            whole = whole + self.buffer[:self.pending_bytes + len(packets.LINE_TERMINATOR)]
            self.buffer = self.buffer[self.pending_bytes + len(packets.LINE_TERMINATOR):]
            self.pending_header = None
            self.pending_bytes = 0
            yield (PROTOCOL_MESSAGE_KIND, whole)


def build_connect_command(socket_token, signature):
    """
    Build the CONNECT operation that authenticates the NATS session.

    The field names and the shape of the signature were taken from nats-py's source rather than invented: a client authenticating with a JSON Web Token sends it as "jwt" and signs the server's nonce, sending the signature as "sig". The NATS server tries unpadded base64url first and falls back to standard base64, so the unpadded form this project's sign_nonce produces is accepted.

    Args:
        socket_token (str): The socket token minted for this session's public key.
        signature (str): The nonce's signature, from credentials.sign_nonce.

    Returns:
        bytes: The complete CONNECT operation, terminator included.
    """
    options = {
        "verbose": False,
        "pedantic": False,
        "lang": CONNECT_LANG,
        "version": CONNECT_VERSION,
        "protocol": CONNECT_PROTOCOL,
        "name": CONNECT_NAME,
        "jwt": socket_token,
        "sig": signature,
    }
    return b"CONNECT " + json.dumps(options).encode("utf-8") + packets.LINE_TERMINATOR


class GrowwConnection:
    """
    Drives one Groww NATS-over-websocket connection and keeps it subscribed.

    Attributes:
        socket_token (str): The socket token minted for this session's public key, presented in CONNECT.
        seed (bytes): The private key whose signature answers each session's nonce.
        subjects (list[str]): The subjects this connection carries, one per instrument.
        on_frame (collections.abc.Callable): Called as on_frame(arrival_time_nanoseconds, frame) for every complete NATS message operation. It must not block, because it runs on the socket read path.
        on_session_start (collections.abc.Callable | None): Called with no arguments each time a new session has authenticated, before anything is subscribed, or None to ignore it.
        logger (logging.Logger | None): Where to report connection events, or None to stay silent.
        maximum_reconnect_attempts (int | None): Give up after this many consecutive failures, or None to keep trying until stopped. Zero means do not reconnect at all, which is what capacity probing wants, and the first session's failure is raised to the caller rather than silently dropped.
        connected (bool): Whether a socket is currently open.
        frames_received (int): Websocket frames read since the object was created, of any kind.
        data_frames_received (int): Complete NATS message operations received, which are the frames carrying market data.
        control_frames_received (int): Protocol operations that were not market data, which are the INFO, PING, PONG, +OK and -ERR lines.
        bytes_received (int): Total bytes of websocket frames read.
        subscriptions_sent (int): SUB operations sent since the object was created.
        reconnect_count (int): Times this object has reconnected since it was created.
        last_data_frame_at (float | None): Monotonic time of the most recent market data message, or None if there has not been one.
        connected_at (float | None): Monotonic time of the most recent successful websocket open.
        ever_connected (bool): Whether any session has ever completed the NATS handshake, which is what tells a credential failure apart from a limit.
    """

    def __init__(self, socket_token, seed, subjects, on_frame, on_session_start=None, logger=None, maximum_reconnect_attempts=None):
        """
        Prepare a connection without opening it.

        Args:
            socket_token (str): The socket token from credentials.websocket_credentials.
            seed (bytes): The thirty two private bytes from credentials.websocket_credentials.
            subjects (list[str]): The subjects this connection should carry, for example "/ld/eq/nse/price_detailed.2885".
            on_frame (collections.abc.Callable): Called as on_frame(arrival_time_nanoseconds, frame) for every complete NATS message operation.
            on_session_start (collections.abc.Callable | None): Called with no arguments each time a new session has authenticated, before anything is subscribed, or None to ignore it. Nothing is stateful across sessions for this broker, so nothing needs discarding, but the callback keeps the contract the other brokers' connections offer.
            logger (logging.Logger | None): Where to report connection events, or None to stay silent.
            maximum_reconnect_attempts (int | None): Give up after this many consecutive failures, or None to keep trying until stopped. Zero means do not reconnect at all, which is what capacity probing wants.

        Returns:
            None.
        """
        self.socket_token = socket_token
        self.seed = seed
        self.subjects = list(subjects)
        self.on_frame = on_frame
        self.on_session_start = on_session_start
        self.logger = logger
        self.maximum_reconnect_attempts = maximum_reconnect_attempts

        self.connected = False
        self.frames_received = 0
        self.data_frames_received = 0
        self.control_frames_received = 0
        self.bytes_received = 0
        self.subscriptions_sent = 0
        self.reconnect_count = 0
        self.last_data_frame_at = None
        self.connected_at = None
        self.ever_connected = False

        self.next_subscription_identifier = 1

    def seconds_since_last_data_frame(self):
        """
        Say how long it has been since a message carrying actual data arrived.

        Only complete NATS message operations refresh the clock, so handshakes, pings and acknowledgements never make a silent connection look served. A connection that is subscribed, open, and quiet apart from pings is the signature of a subscription that was accepted and then quietly not honoured.

        Returns:
            float | None: Seconds since the last market data message, or None when none has ever arrived on this connection.
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

    def _raise_for_error(self, line):
        """
        Turn a -ERR operation into the exception the supervisor should see.

        The same authorization failure means two different things depending on history. On the first session ever to authenticate the socket token itself is wrong or expired, which no amount of retrying will fix. On a later session, while earlier ones worked, the credentials are fine and this connection was one too many, which is how a bus at its limit says no. An error naming a maximum is a refusal in every case, and anything else is an ordinary protocol error the reconnection loop can handle.

        Args:
            line (bytes): The -ERR operation line as received.

        Returns:
            None.

        Raises:
            GrowwAuthenticationError: On an authorization failure during the first session ever.
            GrowwConnectionRefusedError: On an authorization failure on a later session, or on an error naming a maximum.
            GrowwConnectionError: On any other error, for the reconnection loop.
        """
        text = line.decode("utf-8", errors="ignore")
        lowered = text.lower()

        if "maximum" in lowered:
            raise GrowwConnectionRefusedError(
                "maximum_reached",
                f"Groww answered with {text!r}, which is how the bus refuses a connection or subscription beyond its limit.",
            )

        if "authorization" in lowered or "authentication" in lowered:
            if not self.ever_connected:
                raise GrowwAuthenticationError(
                    f"Groww answered the handshake with {text!r}: the socket token is most likely expired or its key does not match."
                )
            raise GrowwConnectionRefusedError(
                "authorization_violation",
                f"Groww answered with {text!r} on a session that follows ones which worked, which is how it refuses a connection it has no room for.",
            )

        raise GrowwConnectionError(f"Groww sent an error operation: {text!r}")

    async def _handshake(self, websocket, reader):
        """
        Read the server's INFO, answer it with CONNECT, and wait for the PONG.

        The nonce is fresh per connection, so the signature is made here per session and the seed is never sent anywhere. A socket that opens but never answers is not a working connection, so a missing PONG counts as a refusal rather than as a slow server.

        Args:
            websocket: The open websocket connection to authenticate on.
            reader (ProtocolReader): The reader already fed with any bytes that arrived before this call.

        Returns:
            None.

        Raises:
            GrowwConnectionRefusedError: If the server's INFO carries no nonce, or no PONG arrives within the timeout.
            GrowwAuthenticationError: If the server rejects the credentials during the first session ever.
            GrowwConnectionError: If the server rejects them on a later session, or answers with any other error.
            websockets.exceptions.ConnectionClosed: If the connection drops while authenticating.
        """
        nonce = None
        deadline = time.monotonic() + HANDSHAKE_TIMEOUT_SECONDS

        while nonce is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise GrowwConnectionRefusedError(
                    "handshake_info_timeout",
                    f"Groww sent no INFO carrying a nonce within {HANDSHAKE_TIMEOUT_SECONDS:.0f} seconds.",
                )

            message = await asyncio.wait_for(websocket.recv(), timeout=remaining)
            frame = message if isinstance(message, bytes) else message.encode("utf-8")
            for kind, content in reader.feed(frame):
                if kind != PROTOCOL_OPERATION_KIND:
                    continue
                if content.startswith(b"INFO"):
                    document = json.loads(content[len(b"INFO"):])
                    nonce = document.get("nonce")

        signature = credentials.sign_nonce(self.seed, nonce.encode("utf-8"))
        await websocket.send(build_connect_command(self.socket_token, signature))
        await websocket.send(b"PING" + packets.LINE_TERMINATOR)

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise GrowwConnectionRefusedError(
                    "handshake_pong_timeout",
                    f"Groww sent no PONG within {HANDSHAKE_TIMEOUT_SECONDS:.0f} seconds of the CONNECT.",
                )

            message = await asyncio.wait_for(websocket.recv(), timeout=remaining)
            frame = message if isinstance(message, bytes) else message.encode("utf-8")
            for kind, content in reader.feed(frame):
                if kind != PROTOCOL_OPERATION_KIND:
                    continue
                if content.startswith(b"PONG"):
                    return
                if content.startswith(b"-ERR"):
                    self._raise_for_error(content)

    async def _subscribe(self, websocket):
        """
        Subscribe every subject this connection carries.

        One SUB operation is sent per subject, with a subscription identifier unique within this session, and the operations are sent in batches of a few hundred per websocket write. NATS processes operations in order and says nothing back when a SUB succeeds, so silence here is success; a refusal arrives as -ERR and is raised from the read loop. NATS retains no subscription state across connections, so this runs on every session including reconnections.

        Args:
            websocket: The open websocket connection to subscribe on.

        Returns:
            None.

        Raises:
            websockets.exceptions.ConnectionClosed: If the connection drops while subscribing.
        """
        self.next_subscription_identifier = 1
        for start in range(0, len(self.subjects), SUBSCRIBE_BATCH_SIZE):
            batch = self.subjects[start:start + SUBSCRIBE_BATCH_SIZE]
            operations = b""
            for subject in batch:
                operations = operations + b"SUB " + subject.encode("ascii") + b" " + str(self.next_subscription_identifier).encode("ascii") + packets.LINE_TERMINATOR
                self.next_subscription_identifier = self.next_subscription_identifier + 1
                self.subscriptions_sent = self.subscriptions_sent + 1
            await websocket.send(operations)

    async def _send_pings(self, websocket):
        """
        Send a NATS PING every sixty seconds until cancelled.

        The websockets library's own pings detect a half-open socket. This is what keeps the bus from closing a healthy one for silence, which is a different job, so both run.

        Args:
            websocket: The open websocket connection to ping.

        Returns:
            None.

        Raises:
            websockets.exceptions.ConnectionClosed: If the connection drops while pinging.
        """
        try:
            while True:
                await asyncio.sleep(NATS_PING_INTERVAL_SECONDS)
                await websocket.send(b"PING" + packets.LINE_TERMINATOR)
        except asyncio.CancelledError:
            return

    async def _handle_operation(self, websocket, line):
        """
        Act on one protocol operation that is not market data.

        The only operations that need acting on are the server's PINGs, which keep the connection alive by being answered, and the server's errors, which end the session. Everything else is counted and ignored.

        Args:
            websocket: The open websocket connection to answer on.
            line (bytes): The operation line without its terminator.

        Returns:
            None.

        Raises:
            GrowwAuthenticationError: If the server rejected the credentials during the first session ever.
            GrowwConnectionRefusedError: If the server refused this connection.
            GrowwConnectionError: If the server answered with any other error.
            websockets.exceptions.ConnectionClosed: If the connection drops while answering.
        """
        if line.startswith(b"PING"):
            await websocket.send(b"PONG" + packets.LINE_TERMINATOR)
        elif line.startswith(b"-ERR"):
            self._raise_for_error(line)

    async def _run_one_session(self, stop_event):
        """
        Open one connection, authenticate, subscribe, and read messages until it closes or is stopped.

        Args:
            stop_event (asyncio.Event): Set this to ask the session to close cleanly.

        Returns:
            None.

        Raises:
            GrowwAuthenticationError: If Groww rejected the credentials.
            GrowwConnectionRefusedError: If Groww refused this connection, whether by handshake status, by an early close, or by never answering the handshake.
            GrowwConnectionError: If the byte stream became unreadable, or the first session failed in probe mode.
            websockets.exceptions.ConnectionClosed: If an established connection dropped for an ordinary reason.
        """
        try:
            websocket = await connect(
                WEBSOCKET_URL,
                ping_interval=WEBSOCKET_PING_INTERVAL_SECONDS,
                ping_timeout=WEBSOCKET_PING_TIMEOUT_SECONDS,
                open_timeout=OPEN_TIMEOUT_SECONDS,
                close_timeout=CLOSE_TIMEOUT_SECONDS,
                max_size=MAXIMUM_FRAME_BYTES,
                compression=None,
            )
        except InvalidStatus as error:
            status_code = getattr(getattr(error, "response", None), "status_code", None)
            if status_code in AUTHENTICATION_STATUS_CODES:
                raise GrowwAuthenticationError(
                    f"Groww rejected the websocket handshake with status {status_code}. The socket token is most likely expired."
                ) from error
            raise GrowwConnectionRefusedError(
                f"handshake_status_{status_code}",
                f"Groww refused the websocket handshake with status {status_code}.",
            ) from error

        self.connected = True
        self.connected_at = time.monotonic()
        self._log("info", f"connected, subscribing {len(self.subjects)} subjects")

        reader = ProtocolReader()
        ping_task = None
        try:
            await self._handshake(websocket, reader)
            self.ever_connected = True
            self._log("info", "authenticated with the bus, nonce signed and PONG received")
            if self.on_session_start is not None:
                self.on_session_start()
            await self._subscribe(websocket)

            ping_task = asyncio.create_task(self._send_pings(websocket))
            async for message in websocket:
                frame = message if isinstance(message, bytes) else message.encode("utf-8")
                self.frames_received = self.frames_received + 1
                self.bytes_received = self.bytes_received + len(frame)

                for kind, content in reader.feed(frame):
                    if kind == PROTOCOL_MESSAGE_KIND:
                        self.data_frames_received = self.data_frames_received + 1
                        self.last_data_frame_at = time.monotonic()
                        self.on_frame(time.time_ns(), content)
                    else:
                        self.control_frames_received = self.control_frames_received + 1
                        await self._handle_operation(websocket, content)

                if stop_event.is_set():
                    break
        except ConnectionClosed as error:
            open_for = time.monotonic() - self.connected_at
            code = getattr(getattr(error, "rcvd", None), "code", None)
            if open_for < EARLY_CLOSE_SECONDS and code in REFUSAL_CLOSE_CODES:
                raise GrowwConnectionRefusedError(
                    f"early_close_{code}",
                    f"Groww closed the connection with code {code} after {open_for:.1f} seconds, which is how it refuses a connection it has already accepted.",
                ) from error
            raise
        finally:
            if ping_task is not None:
                ping_task.cancel()
                await asyncio.wait({ping_task})
            self.connected = False
            await websocket.close()

    async def run(self, stop_event):
        """
        Keep a connection open until asked to stop, reconnecting with backoff when it drops.

        Every reconnection authenticates against a fresh nonce and resubscribes from scratch, because the bus remembers no subscription state across connections and a reconnected socket would otherwise stay open and permanently silent.

        The backoff starts at two seconds and doubles to a minute. A refused connection or a rejected credential stops this loop rather than being retried, so the caller can record that the limit has been found or fix the login.

        Args:
            stop_event (asyncio.Event): Set this to bring the connection down cleanly and return.

        Returns:
            None.

        Raises:
            GrowwAuthenticationError: If the credentials were rejected, which no amount of retrying will fix.
            GrowwConnectionRefusedError: If Groww refused the connection, so the caller can record that its limit has been found.
            GrowwConnectionError: If the reconnection attempt limit was reached, or the first session failed in probe mode.
        """
        delay = INITIAL_RECONNECT_SECONDS
        consecutive_failures = 0

        while not stop_event.is_set():
            try:
                await self._run_one_session(stop_event)
                consecutive_failures = 0
                delay = INITIAL_RECONNECT_SECONDS
            except (GrowwAuthenticationError, GrowwConnectionRefusedError):
                raise
            except (ConnectionClosed, OSError, asyncio.TimeoutError, GrowwConnectionError) as error:
                consecutive_failures = consecutive_failures + 1
                self._log("warning", f"connection lost ({type(error).__name__}: {error}); reconnecting in {delay:.0f}s")
                if self.maximum_reconnect_attempts == 0:
                    raise GrowwConnectionError(
                        f"the first session failed ({type(error).__name__}: {error}) and probe mode does not retry."
                    ) from error

            if stop_event.is_set():
                break

            if self.maximum_reconnect_attempts is not None and consecutive_failures > self.maximum_reconnect_attempts:
                raise GrowwConnectionError(
                    f"gave up after {consecutive_failures} consecutive reconnection failures."
                )

            self.reconnect_count = self.reconnect_count + 1
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass
            delay = min(delay * 2, MAXIMUM_RECONNECT_SECONDS)