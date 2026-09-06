"""
Measures how much Groww's feed actually allows, rather than what it documents.

Groww documents up to one thousand instruments at a time against an instrument universe measured in the hundreds of thousands. Every broker measured so far has enforced something other than what it documented, sometimes by more than an order of magnitude, so the real numbers are established by trying rather than trusted.

Two things are measured. How many subscriptions one connection will genuinely accept, and how many connections can be open at once. Both are found by increasing until the answer stops being yes, and both stop at the first refusal rather than probing around it.

The measurement cannot lean on the property the other brokers' probes lean on, and that changes its whole character. Fyers sends a snapshot for every instrument the moment a subscription is accepted, so an instrument missing from the snapshot is an instrument whose subscription was not honoured, and the probe works outside market hours. NATS keeps no retained values: a subscription delivers nothing until the instrument next trades, so outside market hours a fully honoured subscription and a silently truncated one are indistinguishable by data. Instead the probe's success signal is protocol level. A batch of SUB operations is sent, then a PING, and the connection waits for the PONG: NATS processes operations in order, so a PONG proves the server took every SUB before it, and a breach arrives as -ERR ahead of it. This works outside market hours, which is when a probe is safe to run.

One gap remains and it is stated rather than hidden. If the server enforces its limit by quietly ignoring subscriptions beyond it instead of answering -ERR, this probe cannot see that from the protocol, and it would report success at any size. The evidence stored alongside the numbers records exactly what was observed, so a later argument about what the server allowed can be settled from the record.

Run with: python3 -m stream.groww.capacity_probe
"""

import argparse
import asyncio
import json

from sqlalchemy import create_engine, text as sql_text
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from stream.capacity import MARKET_FEED, read_capacity, write_capacity
from stream.groww import connection, credentials
from stream.groww.connection import (
    GrowwAuthenticationError,
    GrowwConnectionError,
    GrowwConnectionRefusedError,
    ProtocolReader,
    WEBSOCKET_URL,
    build_connect_command,
)
from utilities.configuration import postgres_configuration
from utilities.logging import configure_logging

BROKER_NAME = "groww"


class GrowwProbeError(Exception):
    """
    Raised when the probe cannot be run at all, rather than when a limit has been found.
    """


CONNECTION_CEILING = 20
CONNECTION_BASKET_SIZE = 200
CONNECTION_SAFETY_MARGIN = 1

INSTRUMENT_CANDIDATES = [
    1000,
    5000,
    10000,
    20000,
    40000,
    80000,
]
INSTRUMENT_SAFETY_FRACTION = 0.8

PROBE_PATIENCE_SECONDS = 45.0
PROBE_POLL_SECONDS = 0.5
PROBE_STOP_SECONDS = 10.0
SETTLE_PAUSE_SECONDS = 3.0

DOCUMENTED_CONNECTIONS = 1
DOCUMENTED_INSTRUMENTS_PER_CONNECTION = 1000


def live_instruments():
    """
    Read every Groww instrument that is worth subscribing to today, with what it takes to subscribe it.

    Expired contracts are excluded because they will never tick and would make the probe look as though capacity had been consumed by instruments that produce nothing. Rows are taken from the raw instrument master rather than only from the mapped tables, because the subject needs the exchange token and the segment, and the mapped tables do not carry the segment value the subject's path needs.

    The join to the mapping is still what decides which instruments count, so this measures capacity over the instruments this project actually tracks rather than over everything Groww publishes.

    The two dates are looked up first and passed in as parameters rather than written as sub-selects inside the main query. Both raw tables are TimescaleDB hypertables, and a sub-select makes the partitioning column's value a runtime value, which under a parallel plan makes chunk exclusion intermittently exclude every chunk and return no rows.

    Returns:
        list[dict]: One dict per instrument with keys "exchange", "segment" and "exchange_token", sorted by token.

    Raises:
        GrowwProbeError: If either table is empty or the query returns nothing, which must stop the probe rather than let it measure an empty universe.
        sqlalchemy.exc.SQLAlchemyError: If the instrument tables cannot be read.
    """
    engine = create_engine(postgres_configuration["connection_string"])
    with engine.connect() as database_connection:
        download_date = database_connection.execute(sql_text(
            "SELECT max(download_date) FROM instruments.groww"
        )).scalar()
        mapping_date = database_connection.execute(sql_text(
            "SELECT max(mapping_date) FROM instruments.broker_mappings WHERE broker = 'groww'"
        )).scalar()

        if download_date is None:
            raise GrowwProbeError("instruments.groww holds no rows, so the daily instrument download has never run.")
        if mapping_date is None:
            raise GrowwProbeError("instruments.broker_mappings holds no Groww rows, so the daily mapping has never run.")

        rows = database_connection.execute(
            sql_text(
                "SELECT DISTINCT g.exchange, g.segment, g.exchange_token "
                "FROM instruments.groww g "
                "JOIN instruments.broker_mappings b ON b.broker_token = g.exchange_token AND b.broker = 'groww' "
                "JOIN instruments.master m ON m.instrument_id = b.instrument_id "
                "WHERE g.download_date = :download_date "
                "  AND b.mapping_date = :mapping_date "
                "  AND (m.expiry_date IS NULL OR m.expiry_date > CURRENT_DATE) "
                "ORDER BY g.exchange_token"
            ),
            {
                "download_date": download_date,
                "mapping_date": mapping_date,
            },
        ).all()

    if not rows:
        raise GrowwProbeError(
            f"no live Groww instruments were found for download {download_date} and mapping {mapping_date}, so there is nothing to probe with."
        )

    instruments = []
    for row in rows:
        if not row.exchange_token or not row.exchange or not row.segment:
            continue
        instruments.append({
            "exchange": row.exchange,
            "segment": row.segment,
            "exchange_token": row.exchange_token,
        })
    return instruments


def subjects_for(instruments):
    """
    Turn instrument rows into the subjects the feed publishes their quotes on.

    Args:
        instruments (list[dict]): Instrument rows from live_instruments.

    Returns:
        list[str]: One price_detailed subject per instrument, in the order given.
    """
    subjects = []
    for instrument in instruments:
        if instrument["segment"] == "FNO":
            subject_group = "fo"
        else:
            subject_group = "eq"
        subjects.append(f"/ld/{subject_group}/{instrument['exchange'].lower()}/price_detailed.{instrument['exchange_token']}")
    return subjects


class ProbeConnection:
    """
    One throwaway connection that subscribes and confirms acceptance with a PING.

    The production driver in `stream.groww.connection` subscribes and returns to reading, because in normal operation the bus's acceptance is proven by the data that follows. Nothing follows outside market hours, so the probe needs the stronger signal: SUB operations, then a PING, then wait for the PONG that proves every SUB before it was processed. This class is that protocol, kept self-contained so the probe can be read on its own.

    Once the PONG arrives the connection stays open, answering the bus's pings, until `stop_event` is set. That is what lets the connection-count measurement hold earlier connections open: a bus that drops an older connection when a new one arrives would otherwise go unnoticed.

    Attributes:
        socket_token (str): The socket token minted for this probe session's key.
        seed (bytes): The private key that signs each session's nonce.
        subjects (list[str]): The subjects this connection subscribes.
        reader (ProtocolReader): The NATS byte stream reassembler this connection reads through.
        connected (bool): Whether the websocket is currently open.
        accepted (bool): Whether a PONG arrived after every SUB was sent.
        refusal (str | None): What the server said or did when it would not serve this connection.
        messages (int): Market data messages that arrived, which should be zero outside market hours.
        stop_event (asyncio.Event): Set this to bring the connection down.
    """

    def __init__(self, socket_token, seed, subjects):
        """
        Prepare a probe connection without opening it.

        Args:
            socket_token (str): The socket token from credentials.websocket_credentials.
            seed (bytes): The thirty two private bytes from credentials.websocket_credentials.
            subjects (list[str]): The subjects to subscribe.

        Returns:
            None.
        """
        self.socket_token = socket_token
        self.seed = seed
        self.subjects = list(subjects)
        self.reader = ProtocolReader()

        self.connected = False
        self.accepted = False
        self.refusal = None
        self.messages = 0
        self.stop_event = asyncio.Event()

    async def run(self):
        """
        Open the websocket, authenticate, subscribe, and wait for the confirming PONG.

        The handshake signs a fresh nonce per session, exactly as the production driver does. After subscribing, one PING is sent and the read loop waits: a PONG completes the handshake of subscriptions, a -ERR names the refusal, and a closed socket before either is a refusal by conduct. Once accepted, the same loop keeps the connection alive by answering the bus's PINGs, until `stop_event` is set.

        Returns:
            None.

        Raises:
            GrowwAuthenticationError: If the server rejects the credentials, which the probe must not retry.
            GrowwConnectionError: If the stream becomes unreadable, or the websocket handshake is refused.
            websockets.exceptions.ConnectionClosed: If the socket drops mid-session, which sets refusal rather than raising, because a dropped probe connection is evidence about the limit rather than a fault.
        """
        try:
            websocket = await connect(
                WEBSOCKET_URL,
                ping_interval=connection.WEBSOCKET_PING_INTERVAL_SECONDS,
                ping_timeout=connection.WEBSOCKET_PING_TIMEOUT_SECONDS,
                open_timeout=connection.OPEN_TIMEOUT_SECONDS,
                close_timeout=connection.CLOSE_TIMEOUT_SECONDS,
                max_size=connection.MAXIMUM_FRAME_BYTES,
                compression=None,
            )
        except InvalidStatus as error:
            status_code = getattr(getattr(error, "response", None), "status_code", None)
            if status_code in connection.AUTHENTICATION_STATUS_CODES:
                raise GrowwAuthenticationError(
                    f"Groww rejected the websocket handshake with status {status_code}. The socket token is most likely expired."
                ) from error
            raise GrowwConnectionRefusedError(
                f"handshake_status_{status_code}",
                f"Groww refused the websocket handshake with status {status_code}.",
            ) from error

        self.connected = True
        try:
            nonce = None
            while nonce is None:
                message = await asyncio.wait_for(websocket.recv(), timeout=connection.HANDSHAKE_TIMEOUT_SECONDS)
                frame = message if isinstance(message, bytes) else message.encode("utf-8")
                for kind, content in self.reader.feed(frame):
                    if kind == connection.PROTOCOL_OPERATION_KIND and content.startswith(b"INFO"):
                        document = json_document(content)
                        nonce = document.get("nonce")

            signature = credentials.sign_nonce(self.seed, nonce.encode("utf-8"))
            await websocket.send(build_connect_command(self.socket_token, signature))
            await websocket.send(b"PING" + connection.packets.LINE_TERMINATOR)

            authenticated = False
            while not authenticated:
                message = await asyncio.wait_for(websocket.recv(), timeout=connection.HANDSHAKE_TIMEOUT_SECONDS)
                frame = message if isinstance(message, bytes) else message.encode("utf-8")
                for kind, content in self.reader.feed(frame):
                    if kind != connection.PROTOCOL_OPERATION_KIND:
                        continue
                    if content.startswith(b"PONG"):
                        authenticated = True
                        break
                    if content.startswith(b"-ERR"):
                        raise error_for_line(content, ever_connected=False)
            if not authenticated:
                raise GrowwConnectionError("the websocket closed before the handshake completed.")

            operations = b""
            for subscription_identifier, subject in enumerate(self.subjects, start=1):
                operations = operations + b"SUB " + subject.encode("ascii") + b" " + str(subscription_identifier).encode("ascii") + connection.packets.LINE_TERMINATOR
                if len(operations) >= 1024 * 1024:
                    await websocket.send(operations)
                    operations = b""
            if operations:
                await websocket.send(operations)
            await websocket.send(b"PING" + connection.packets.LINE_TERMINATOR)

            while not self.stop_event.is_set():
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=PROBE_POLL_SECONDS)
                except asyncio.TimeoutError:
                    continue
                except ConnectionClosed:
                    if not self.accepted and self.refusal is None:
                        self.refusal = "the bus closed the connection before confirming the subscriptions."
                    return

                frame = message if isinstance(message, bytes) else message.encode("utf-8")
                for kind, content in self.reader.feed(frame):
                    if kind == connection.PROTOCOL_MESSAGE_KIND:
                        self.messages = self.messages + 1
                    elif content.startswith(b"PONG"):
                        self.accepted = True
                    elif content.startswith(b"PING"):
                        await websocket.send(b"PONG" + connection.packets.LINE_TERMINATOR)
                    elif content.startswith(b"-ERR"):
                        raise error_for_line(content, ever_connected=True)
        except ConnectionClosed:
            if not self.accepted and self.refusal is None:
                self.refusal = "the bus closed the connection mid-probe."
        finally:
            self.connected = False
            await websocket.close()


def json_document(info_line):
    """
    Parse the JSON out of an INFO operation line.

    Args:
        info_line (bytes): The INFO line without its terminator.

    Returns:
        dict: The parsed document.
    """
    return json.loads(info_line[len(b"INFO"):])


def error_for_line(line, ever_connected):
    """
    Turn a -ERR operation into the exception the probe should see.

    The same authorization failure means two different things depending on history, exactly as in the production driver: before any session has ever authenticated it means the credentials are wrong, and afterwards it means this connection was one too many. An error naming a maximum is a refusal in every case.

    Args:
        line (bytes): The -ERR operation line as received.
        ever_connected (bool): Whether any session has ever completed the handshake before this one.

    Returns:
        Exception: The exception to raise, built but not yet raised.
    """
    text_value = line.decode("utf-8", errors="ignore")
    lowered = text_value.lower()
    if "maximum" in lowered:
        return GrowwConnectionRefusedError(
            "maximum_reached",
            f"Groww answered with {text_value!r}, which is how the bus refuses a subscription or connection beyond its limit.",
        )
    if "authorization" in lowered or "authentication" in lowered:
        if not ever_connected:
            return GrowwAuthenticationError(
                f"Groww answered the handshake with {text_value!r}: the socket token is most likely expired or its key does not match."
            )
        return GrowwConnectionRefusedError(
            "authorization_violation",
            f"Groww answered with {text_value!r} on a session that follows ones which worked, which is how it refuses a connection it has no room for.",
        )
    return GrowwConnectionError(f"Groww sent an error operation: {text_value!r}")


async def run_probe_session(probe, keep_open=False):
    """
    Run one probe connection to its verdict.

    The verdict is `accepted` or a refusal. When `keep_open` is false the connection is brought down before returning, which is what the instruments-per-connection measurement wants: each candidate gets a fresh connection, so nothing carries over. When it is true and the subscriptions were accepted, the connection is left open and running, and the task that drives it is returned for the caller to stop later.

    Args:
        probe (ProbeConnection): The connection to run.
        keep_open (bool): Whether to leave an accepted connection running.

    Returns:
        asyncio.Task | None: The task still driving the connection when it was left open, or None when the connection was brought down.

    Raises:
        GrowwAuthenticationError: If the server rejected the credentials.
    """
    task = asyncio.create_task(probe.run())
    waited = 0.0
    while waited < PROBE_PATIENCE_SECONDS:
        await asyncio.sleep(PROBE_POLL_SECONDS)
        waited = waited + PROBE_POLL_SECONDS
        if task.done() or probe.accepted or probe.refusal is not None:
            break

    leave_running = keep_open and not task.done() and probe.accepted
    if not leave_running:
        if probe.refusal is None and not probe.accepted:
            probe.refusal = f"no confirmation arrived within {PROBE_PATIENCE_SECONDS:.0f} seconds."
        probe.stop_event.set()

    if task.done() or not leave_running:
        try:
            await asyncio.wait_for(task, timeout=PROBE_STOP_SECONDS)
        except asyncio.TimeoutError:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, GrowwConnectionError):
                pass
        except GrowwConnectionError as error:
            probe.refusal = f"{type(error).__name__}: {error}"
        return None

    return task


async def stop_probe_session(probe, task):
    """
    Bring a probe connection that was left open down cleanly.

    Args:
        probe (ProbeConnection): The connection to stop.
        task (asyncio.Task): The task driving it, from run_probe_session.

    Returns:
        None.
    """
    if task is None:
        return
    probe.stop_event.set()
    try:
        await asyncio.wait_for(task, timeout=PROBE_STOP_SECONDS)
    except (asyncio.TimeoutError, asyncio.CancelledError, GrowwConnectionError):
        if not task.done():
            task.cancel()


async def probe_instruments_per_connection(socket_token, seed, subjects, logger):
    """
    Find the largest number of subscriptions one connection will accept in full.

    Each candidate gets a fresh connection, because a subscription added to an existing one would not distinguish a connection that accepts many subscriptions from one that accepts many connections.

    Args:
        socket_token (str): The socket token from credentials.websocket_credentials.
        seed (bytes): The private key from credentials.websocket_credentials.
        subjects (list[str]): Subjects to draw candidates from.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (largest_accepted, evidence) pair, where evidence is a list of dicts describing each candidate tried.

    Raises:
        GrowwAuthenticationError: If Groww rejected the credentials.
    """
    evidence = []
    largest_accepted = 0

    candidates = []
    for candidate in INSTRUMENT_CANDIDATES:
        if candidate < len(subjects):
            candidates.append(candidate)
    candidates.append(len(subjects))

    for candidate in candidates:
        probe = ProbeConnection(socket_token, seed, subjects[:candidate])
        await run_probe_session(probe)

        evidence.append({
            "candidate_subjects": candidate,
            "accepted": probe.accepted,
            "messages_during_probe": probe.messages,
            "detail": probe.refusal,
        })
        logger.info(
            f"instruments per connection: subscribed {candidate}, "
            f"{'accepted' if probe.accepted else 'NOT accepted'}"
            f"{' - ' + probe.refusal if probe.refusal else ''}"
        )

        if probe.refusal or not probe.accepted:
            break
        largest_accepted = candidate
        await asyncio.sleep(SETTLE_PAUSE_SECONDS)

    return (largest_accepted, evidence)


async def probe_connection_count(socket_token, seed, subjects, ceiling, logger):
    """
    Find how many connections can be open at once, holding every earlier one open while testing the next.

    Each connection gets a small basket of subjects rather than none, because a bus might tolerate a connection that subscribes to nothing and still count it, which would overstate capacity. Earlier connections are held rather than closed because the question is how many the account supports simultaneously, and because a bus that drops an older connection when a new one arrives would otherwise go unnoticed; their liveness is read from `connected` before each new attempt.

    Args:
        socket_token (str): The socket token from credentials.websocket_credentials.
        seed (bytes): The private key from credentials.websocket_credentials.
        subjects (list[str]): Subjects to build each connection's basket from.
        ceiling (int): Stop at this many connections even if none has been refused, so a runaway probe cannot look like an attack on the broker.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (working_connections, refusal_reason, evidence) triple.

    Raises:
        GrowwAuthenticationError: If Groww rejected the credentials.
    """
    evidence = []
    held = []
    refusal_reason = None

    for number in range(ceiling):
        basket = subjects[number * CONNECTION_BASKET_SIZE:(number + 1) * CONNECTION_BASKET_SIZE]
        if not basket:
            break

        probe = ProbeConnection(socket_token, seed, basket)
        running_task = await run_probe_session(probe, keep_open=True)
        if running_task is None:
            refusal_reason = probe.refusal or "connection_closed_after_acceptance"
            break

        still_open = 0
        for earlier_probe, earlier_task in held:
            if earlier_probe.connected:
                still_open = still_open + 1

        evidence.append({
            "connection_number": number + 1,
            "basket_size": len(basket),
            "accepted": probe.accepted,
            "earlier_connections_still_open": still_open,
            "detail": probe.refusal,
        })
        logger.info(
            f"connection {number + 1}: {'accepted' if probe.accepted else 'NOT accepted'}, "
            f"{still_open} of {len(held)} earlier connections still open"
            f"{' - ' + probe.refusal if probe.refusal else ''}"
        )

        if probe.refusal or not probe.accepted:
            refusal_reason = probe.refusal or "subscriptions_not_confirmed"
            break
        if still_open != len(held):
            refusal_reason = "earlier_connection_dropped"
            break

        held.append((probe, running_task))
        await asyncio.sleep(SETTLE_PAUSE_SECONDS)

    for probe, task in held:
        await stop_probe_session(probe, task)

    return (len(held), refusal_reason, evidence)


async def run_probe(ceiling, store):
    """
    Measure both limits and record the results.

    Args:
        ceiling (int): The largest number of connections to attempt.
        store (bool): Whether to write the measurements to MongoDB.

    Returns:
        int: 0 when the probe completed, 1 when it could not measure anything.

    Raises:
        GrowwAuthenticationError: If Groww rejected the credentials.
    """
    logger = configure_logging("stream_groww_capacity_probe")
    socket_token, seed = credentials.websocket_credentials()

    instruments = live_instruments()
    subjects = subjects_for(instruments)
    logger.info(f"probing with {len(subjects)} subjects built from {len(instruments)} live instruments")

    largest_subjects, instrument_evidence = await probe_instruments_per_connection(socket_token, seed, subjects, logger)
    await asyncio.sleep(SETTLE_PAUSE_SECONDS)
    working_connections, refusal_reason, connection_evidence = await probe_connection_count(socket_token, seed, subjects, ceiling, logger)

    if largest_subjects == 0 or working_connections == 0:
        logger.error("the probe could not establish either limit")
        return 1

    connection_count = max(1, working_connections - CONNECTION_SAFETY_MARGIN)
    subjects_per_connection = int(largest_subjects * INSTRUMENT_SAFETY_FRACTION)

    print()
    print("=" * 78)
    print("  market feed")
    print(f"  largest subscription batch accepted on one connection : {largest_subjects:,}")
    print(f"  simultaneous connections that were accepted           : {working_connections}")
    print(f"  stopped because                                       : {refusal_reason or 'the ceiling was reached'}")
    print()
    print(f"  recommended connection_count                          : {connection_count}  (measured minus {CONNECTION_SAFETY_MARGIN})")
    print(f"  recommended instruments_per_connection                : {subjects_per_connection:,}  ({INSTRUMENT_SAFETY_FRACTION:.0%} of measured)")
    print(f"  that covers                                           : {connection_count * subjects_per_connection:,} instruments")
    print(f"  the live universe needs                               : {len(subjects):,}")
    print(f"  Groww documents                                       : {DOCUMENTED_CONNECTIONS} connection x {DOCUMENTED_INSTRUMENTS_PER_CONNECTION:,} instruments")
    print("=" * 78)

    if store:
        document = write_capacity(
            BROKER_NAME,
            connection_count,
            subjects_per_connection,
            refusal_reason,
            instrument_evidence + connection_evidence,
            feed_name=MARKET_FEED,
        )
        print(f"\nstored in MongoDB stream_capacity under {MARKET_FEED}, measured_at {document['measured_at']}")
    return 0


def main():
    """
    Parse the command line and run the capacity probe.

    Returns:
        None.

    Raises:
        SystemExit: Always, with the probe's exit status.
    """
    parser = argparse.ArgumentParser(description="Measure Groww's real feed limits.")
    parser.add_argument("--ceiling", type=int, default=CONNECTION_CEILING, help="Largest number of connections to attempt.")
    parser.add_argument("--no-store", action="store_true", help="Report the measurement without recording it.")
    arguments = parser.parse_args()

    previous = read_capacity(BROKER_NAME, MARKET_FEED)
    if previous is not None:
        print(f"previously measured: {previous['connection_count']} connections x {previous['instruments_per_connection']:,} instruments, at {previous['measured_at']}")
    print()

    raise SystemExit(asyncio.run(run_probe(arguments.ceiling, not arguments.no_store)))


if __name__ == "__main__":
    main()