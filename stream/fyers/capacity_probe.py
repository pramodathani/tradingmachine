"""
Measures how much Fyers' websockets actually allow, rather than what they document.

Fyers documents one websocket connection instance at a time and five thousand subscriptions on it, against an instrument universe of about a hundred and sixty thousand. If those numbers were true, Fyers would cover roughly three per cent of the universe and there would be little point building this at all. Every broker measured so far has enforced something other than what it documented, sometimes by more than an order of magnitude, so the real numbers are established by trying.

Two things are measured on each feed. How many instruments one connection will genuinely serve, and how many connections can be open at once. Both are found by increasing until the answer stops being yes, and both stop at the first refusal rather than probing around it.

The measurement leans on the same convenient property the other brokers' probes lean on: Fyers sends a snapshot for every instrument as soon as it accepts a subscription. So a subscription that was quietly truncated shows up immediately as instruments missing from the snapshot, and the probe works outside market hours, when nothing would otherwise tick. On this broker the snapshot does more than that, because it is also the only packet that names its topic, so an instrument missing from the snapshot is an instrument whose updates could never have been decoded anyway.

The two feeds are measured separately and stored under separate feed names, because they are different sockets with different limits drawing on what may or may not be the same pool. The tick-by-tick feed's documented limit of five symbols is small enough that the probe checks it rather than searching upward from it.

Run with: python3 -m stream.fyers.capacity_probe
"""

import argparse
import asyncio
from datetime import datetime

from sqlalchemy import create_engine, text

from stream.capacity import MARKET_FEED, read_capacity, write_capacity
from stream.fyers import depth_packets, packets
from stream.fyers.connection import (
    FyersAuthenticationError,
    FyersConnection,
    MODE_FULL,
)
from stream.fyers.credentials import authorization_header_value, websocket_credentials
from stream.fyers.depth_connection import (
    DOCUMENTED_SYMBOLS_PER_CONNECTION,
    FyersDepthAuthenticationError,
    FyersDepthConnection,
)
from utilities.configuration import postgres_configuration
from utilities.logging import configure_logging

BROKER_NAME = "fyers"
TICK_BY_TICK_FEED = "tick_by_tick_depth"


class FyersProbeError(Exception):
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

SNAPSHOT_PATIENCE_SECONDS = 120.0
SNAPSHOT_POLL_SECONDS = 0.4
CONNECTION_PATIENCE_SECONDS = 20.0

TICK_BY_TICK_CANDIDATES = [
    1,
    5,
    10,
    25,
]
TICK_BY_TICK_PATIENCE_SECONDS = 30.0
TICK_BY_TICK_CONNECTION_COUNT = 1


def live_instruments():
    """
    Read every Fyers instrument that is worth subscribing to today, with what it takes to subscribe it.

    Two filters matter and both change the answer. Expired contracts are excluded because they will never tick and would make the probe look as though capacity had been consumed by instruments that produce nothing. Rows are taken from the raw instrument master rather than only from the mapped tables, because the subscription key needs the exchange token and the ticker, and neither is a column the mapped tables carry.

    The join to the mapping is still what decides which instruments count, so this measures capacity over the instruments this project actually tracks rather than over everything Fyers publishes.

    The two dates are looked up first and passed in as parameters rather than being written as sub-selects inside the main query. Both raw tables are TimescaleDB hypertables, and a sub-select makes the partitioning column's value a runtime value, which under a parallel plan makes TimescaleDB's chunk exclusion intermittently exclude every chunk and return no rows at all. That was observed here: the identical query returned the right count on some runs and zero on others, on fresh connections, roughly a third of the time. Resolving the dates first makes them plan-time constants and the result stable.

    Returns:
        list[dict]: One dict per instrument with keys "fytoken", "scrip_code", "symbol_ticker" and "segment", sorted by token.

    Raises:
        FyersProbeError: If either table is empty, or the query returns nothing, which must stop the probe rather than let it measure an empty universe.
        sqlalchemy.exc.SQLAlchemyError: If the instrument tables cannot be read.
    """
    engine = create_engine(postgres_configuration["connection_string"])
    with engine.connect() as database_connection:
        download_date = database_connection.execute(text(
            "SELECT max(download_date) FROM instruments.fyers"
        )).scalar()
        mapping_date = database_connection.execute(text(
            "SELECT max(mapping_date) FROM instruments.broker_mappings WHERE broker = 'fyers'"
        )).scalar()

        if download_date is None:
            raise FyersProbeError("instruments.fyers holds no rows, so the daily instrument download has never run.")
        if mapping_date is None:
            raise FyersProbeError("instruments.broker_mappings holds no Fyers rows, so the daily mapping has never run.")

        rows = database_connection.execute(
            text(
                "SELECT DISTINCT f.fytoken, f.scrip_code, f.symbol_ticker "
                "FROM instruments.fyers f "
                "JOIN instruments.broker_mappings b ON b.broker_token = f.fytoken AND b.broker = 'fyers' "
                "JOIN instruments.master m ON m.instrument_id = b.instrument_id "
                "WHERE f.download_date = :download_date "
                "  AND b.mapping_date = :mapping_date "
                "  AND (m.expiry_date IS NULL OR m.expiry_date > CURRENT_DATE) "
                "ORDER BY f.fytoken"
            ),
            {
                "download_date": download_date,
                "mapping_date": mapping_date,
            },
        ).all()

    if not rows:
        raise FyersProbeError(
            f"no live Fyers instruments were found for download {download_date} and mapping {mapping_date}, so there is nothing to probe with."
        )

    instruments = []
    for row in rows:
        segment = packets.segment_for_token(row.fytoken)
        if segment is None:
            continue
        instruments.append({
            "fytoken": row.fytoken,
            "scrip_code": row.scrip_code,
            "symbol_ticker": row.symbol_ticker,
            "segment": segment,
        })
    return instruments


def subscription_keys(instruments, feed=packets.FEED_QUOTE):
    """
    Turn instrument rows into the subscription keys the wire takes.

    Args:
        instruments (list[dict]): Instrument rows from live_instruments.
        feed (str): Which feed the keys are for, "quote" or "depth".

    Returns:
        list[str]: One key per instrument that has one, in the order given.
    """
    keys = []
    for instrument in instruments:
        key = packets.hsm_symbol_for_instrument(instrument["fytoken"], instrument["scrip_code"], instrument["symbol_ticker"], feed)
        if key is not None:
            keys.append(key)
    return keys


class SnapshotCollector:
    """
    Collects the instruments a connection actually delivers, so a truncated subscription can be seen.

    Attributes:
        wanted (set): The subscription keys that were subscribed to.
        seen (set): The topic names that have arrived in a snapshot.
        frames (int): Data frames that have arrived.
        bytes_received (int): Total bytes of those frames.
    """

    def __init__(self, keys):
        """
        Prepare a collector for one subscription.

        Args:
            keys (list[str]): The subscription keys that are being subscribed to.

        Returns:
            None.
        """
        self.wanted = set(keys)
        self.seen = set()
        self.frames = 0
        self.bytes_received = 0

    def reset(self):
        """
        Forget everything seen, which a new session requires.

        Returns:
            None.
        """
        self.seen = set()

    def on_frame(self, arrival_time_nanoseconds, frame):
        """
        Record whatever instruments a frame introduced.

        Only snapshot packets name their topic, which is exactly what makes them the right thing to count: an instrument that never appears in a snapshot is one whose updates this project could not decode even if they arrived.

        Args:
            arrival_time_nanoseconds (int): When the frame was read, which this collector does not use.
            frame (bytes): The frame as received.

        Returns:
            None.
        """
        if packets.frame_response_type(frame) != packets.RESPONSE_TYPE_DATA_FEED:
            return
        self.frames = self.frames + 1
        self.bytes_received = self.bytes_received + len(frame)
        for tick in packets.decode_frame(frame, datetime.now()):
            if tick.get("topic_name"):
                self.seen.add(tick["topic_name"])

    def delivered(self):
        """
        Say how many of the subscribed instruments have arrived.

        Returns:
            int: The count of subscribed instruments seen so far.
        """
        return len(self.wanted & self.seen)

    def is_complete(self):
        """
        Say whether every subscribed instrument has arrived.

        Returns:
            bool: True when the subscription was honoured in full.
        """
        return self.wanted <= self.seen


class DepthCollector:
    """
    Collects the instruments a tick-by-tick connection actually delivers.

    Attributes:
        wanted (set): The symbol tickers that were subscribed to.
        seen (set): The tickers that have arrived.
        errors (list): Error texts the server sent, which is how it reports a symbol it will not serve.
        frames (int): Data frames that have arrived.
        bytes_received (int): Total bytes of those frames.
    """

    def __init__(self, symbol_tickers):
        """
        Prepare a collector for one subscription.

        Args:
            symbol_tickers (list[str]): The tickers that are being subscribed to.

        Returns:
            None.
        """
        self.wanted = set(symbol_tickers)
        self.seen = set()
        self.errors = []
        self.frames = 0
        self.bytes_received = 0

    def on_frame(self, arrival_time_nanoseconds, frame):
        """
        Record whatever instruments a frame carried.

        Args:
            arrival_time_nanoseconds (int): When the frame was read, which this collector does not use.
            frame (bytes): The frame as received.

        Returns:
            None.
        """
        ticks = depth_packets.decode_frame(frame, datetime.now())
        if not ticks:
            return
        self.frames = self.frames + 1
        self.bytes_received = self.bytes_received + len(frame)
        for tick in ticks:
            if tick.get("ticker"):
                self.seen.add(tick["ticker"])

    def on_error_message(self, text_value):
        """
        Record an error the server reported.

        Args:
            text_value (str): The error text.

        Returns:
            None.
        """
        self.errors.append(text_value)

    def delivered(self):
        """
        Say how many of the subscribed instruments have arrived.

        Returns:
            int: The count of subscribed instruments seen so far.
        """
        return len(self.wanted & self.seen)

    def is_complete(self):
        """
        Say whether every subscribed instrument has arrived.

        Returns:
            bool: True when the subscription was honoured in full.
        """
        return self.wanted <= self.seen


async def open_and_collect(hsm_key, keys, patience_seconds):
    """
    Open one quote connection, subscribe, and wait for the snapshot to arrive in full.

    Args:
        hsm_key (str): The hsm_key claim decoded out of today's access token.
        keys (list[str]): The subscription keys to subscribe.
        patience_seconds (float): How long to wait for every instrument to arrive before giving up.

    Returns:
        tuple: A (collector, connection, task, stop_event, refusal) tuple, where refusal is None when the connection was accepted and a string describing the refusal otherwise. The connection is left open so the caller can decide when to close it.

    Raises:
        FyersAuthenticationError: If Fyers rejected the credentials.
    """
    collector = SnapshotCollector(keys)
    live_connection = FyersConnection(
        hsm_key=hsm_key,
        instruments=keys,
        on_frame=collector.on_frame,
        mode=MODE_FULL,
        on_session_start=collector.reset,
        maximum_reconnect_attempts=0,
    )
    stop_event = asyncio.Event()
    task = asyncio.create_task(live_connection.run(stop_event))

    refusal = None
    waited = 0.0
    while waited < patience_seconds:
        await asyncio.sleep(SNAPSHOT_POLL_SECONDS)
        waited = waited + SNAPSHOT_POLL_SECONDS
        if collector.is_complete():
            break
        if task.done():
            exception = task.exception()
            if isinstance(exception, FyersAuthenticationError):
                raise exception
            if exception is not None:
                refusal = f"{type(exception).__name__}: {exception}"
            break

    return (collector, live_connection, task, stop_event, refusal)


async def close_probe(task, stop_event):
    """
    Bring one probe connection down without waiting on it indefinitely.

    Args:
        task (asyncio.Task): The task running the connection.
        stop_event (asyncio.Event): The event that asks it to stop.

    Returns:
        None.
    """
    stop_event.set()
    if not task.done():
        try:
            await asyncio.wait_for(task, timeout=10)
        except (asyncio.TimeoutError, Exception):
            task.cancel()


async def probe_instruments_per_connection(hsm_key, keys, logger):
    """
    Find the largest number of instruments one connection will serve in full.

    Each candidate gets a fresh connection, because a subscription added to an existing one would not distinguish a connection that accepts many instruments from one that accepts many subscriptions.

    Args:
        hsm_key (str): The hsm_key claim decoded out of today's access token.
        keys (list[str]): Subscription keys to draw candidates from.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (largest_complete, evidence) pair, where evidence is a list of dicts describing each candidate tried.

    Raises:
        FyersAuthenticationError: If Fyers rejected the credentials.
    """
    evidence = []
    largest_complete = 0

    candidates = []
    for candidate in INSTRUMENT_CANDIDATES:
        if candidate < len(keys):
            candidates.append(candidate)
    candidates.append(len(keys))

    for candidate in candidates:
        chosen = keys[:candidate]
        collector, live_connection, task, stop_event, refusal = await open_and_collect(
            hsm_key, chosen, SNAPSHOT_PATIENCE_SECONDS
        )
        complete = collector.is_complete()
        await close_probe(task, stop_event)

        evidence.append({
            "candidate_instruments": candidate,
            "delivered": collector.delivered(),
            "frames": collector.frames,
            "bytes_received": collector.bytes_received,
            "outcome": "complete" if complete else ("refused" if refusal else "incomplete"),
            "detail": refusal,
        })
        logger.info(
            f"instruments per connection: subscribed {candidate}, delivered {collector.delivered()}, "
            f"{'complete' if complete else 'INCOMPLETE'}{' - ' + refusal if refusal else ''}"
        )

        if refusal or not complete:
            break
        largest_complete = candidate
        await asyncio.sleep(3)

    return (largest_complete, evidence)


async def probe_connection_count(hsm_key, keys, ceiling, logger):
    """
    Find how many connections can be open at once, holding every earlier one open while testing the next.

    Earlier connections are held rather than closed because the question is how many the account supports simultaneously, and because a broker that starves an older connection when a new one arrives would otherwise go unnoticed. Fyers documents a single connection, so this is the measurement most likely to disagree with the documentation, in either direction.

    Args:
        hsm_key (str): The hsm_key claim decoded out of today's access token.
        keys (list[str]): Subscription keys to build a small basket for each connection from.
        ceiling (int): Stop at this many connections even if none has been refused, so a runaway probe cannot look like an attack on the broker.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (working_connections, refusal_reason, evidence) triple.

    Raises:
        FyersAuthenticationError: If Fyers rejected the credentials.
    """
    evidence = []
    open_probes = []
    refusal_reason = None

    for number in range(ceiling):
        basket = keys[number * CONNECTION_BASKET_SIZE:(number + 1) * CONNECTION_BASKET_SIZE]
        if not basket:
            break
        collector, live_connection, task, stop_event, refusal = await open_and_collect(
            hsm_key, basket, CONNECTION_PATIENCE_SECONDS
        )
        complete = collector.is_complete()
        earlier_still_open = 0
        for probe in open_probes:
            if probe[1].connected:
                earlier_still_open = earlier_still_open + 1

        evidence.append({
            "connection_number": number + 1,
            "delivered": collector.delivered(),
            "basket_size": len(basket),
            "outcome": "complete" if complete else ("refused" if refusal else "incomplete"),
            "earlier_connections_still_open": earlier_still_open,
            "detail": refusal,
        })
        logger.info(
            f"connection {number + 1}: {'serving' if complete else 'NOT serving'}, "
            f"{earlier_still_open} of {len(open_probes)} earlier connections still open"
            f"{' - ' + refusal if refusal else ''}"
        )

        if refusal or not complete:
            refusal_reason = refusal or "snapshot_not_delivered"
            await close_probe(task, stop_event)
            break
        if earlier_still_open != len(open_probes):
            refusal_reason = "earlier_connection_dropped"
            await close_probe(task, stop_event)
            break

        open_probes.append((collector, live_connection, task, stop_event))
        await asyncio.sleep(1.0)

    working = len(open_probes)
    for probe in open_probes:
        await close_probe(probe[2], probe[3])

    return (working, refusal_reason, evidence)


async def probe_tick_by_tick(authorization, instruments, logger):
    """
    Measure the tick-by-tick depth socket, which documents a limit small enough to check directly.

    Fyers documents five symbols per connection and three connections. Five is small enough that searching upward from it costs almost nothing, so this tries a handful of sizes rather than doubling, and reports the errors the server returns, which is how it names a symbol it will not serve tick-by-tick data for.

    Args:
        authorization (str): The Authorization header value for the depth socket.
        instruments (list[dict]): Instrument rows to draw symbols from.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (largest_complete, refusal_reason, evidence) triple.

    Raises:
        FyersDepthAuthenticationError: If Fyers rejected the credentials.
    """
    evidence = []
    largest_complete = 0
    refusal_reason = None

    eligible = []
    for instrument in instruments:
        if instrument["segment"] in ("nse_cm", "nse_fo") and not packets.is_index_ticker(instrument["symbol_ticker"]):
            eligible.append(instrument["symbol_ticker"])

    if not eligible:
        logger.warning("no NSE cash or futures and options instruments to probe the tick-by-tick feed with")
        return (0, "no_eligible_instruments", evidence)

    for candidate in TICK_BY_TICK_CANDIDATES:
        if candidate > len(eligible):
            break
        chosen = eligible[:candidate]
        collector = DepthCollector(chosen)
        depth_connection = FyersDepthConnection(
            authorization=authorization,
            symbols=chosen,
            on_frame=collector.on_frame,
            on_error_message=collector.on_error_message,
            maximum_reconnect_attempts=0,
        )
        stop_event = asyncio.Event()
        task = asyncio.create_task(depth_connection.run(stop_event))

        refusal = None
        waited = 0.0
        while waited < TICK_BY_TICK_PATIENCE_SECONDS:
            await asyncio.sleep(SNAPSHOT_POLL_SECONDS)
            waited = waited + SNAPSHOT_POLL_SECONDS
            if collector.is_complete():
                break
            if task.done():
                exception = task.exception()
                if isinstance(exception, FyersDepthAuthenticationError):
                    raise exception
                if exception is not None:
                    refusal = f"{type(exception).__name__}: {exception}"
                break

        complete = collector.is_complete()
        await close_probe(task, stop_event)

        evidence.append({
            "feed": TICK_BY_TICK_FEED,
            "candidate_symbols": candidate,
            "delivered": collector.delivered(),
            "frames": collector.frames,
            "bytes_received": collector.bytes_received,
            "outcome": "complete" if complete else ("refused" if refusal else "incomplete"),
            "server_errors": collector.errors[:5],
            "detail": refusal,
        })
        logger.info(
            f"tick-by-tick: subscribed {candidate}, delivered {collector.delivered()}, "
            f"{'complete' if complete else 'INCOMPLETE'}"
            f"{' - ' + refusal if refusal else ''}"
            f"{' - server said ' + '; '.join(collector.errors[:3]) if collector.errors else ''}"
        )

        if refusal or not complete:
            refusal_reason = refusal or "depth_not_delivered"
            break
        largest_complete = candidate
        await asyncio.sleep(3)

    return (largest_complete, refusal_reason, evidence)


async def run_probe(ceiling, store, include_tick_by_tick):
    """
    Measure both limits on the quote feed, optionally measure the tick-by-tick feed, and record the results.

    Args:
        ceiling (int): The largest number of connections to attempt.
        store (bool): Whether to write the measurements to MongoDB.
        include_tick_by_tick (bool): Whether to measure the tick-by-tick depth feed as well.

    Returns:
        int: 0 when the probe completed, 1 when it could not measure anything.

    Raises:
        FyersAuthenticationError: If Fyers rejected the credentials.
    """
    logger = configure_logging("stream_fyers_capacity_probe")
    application_identifier, access_token, hsm_key = websocket_credentials()

    instruments = live_instruments()
    keys = subscription_keys(instruments, packets.FEED_QUOTE)
    logger.info(f"probing with {len(keys)} subscription keys built from {len(instruments)} live instruments")
    if len(keys) != len(instruments):
        logger.warning(f"{len(instruments) - len(keys)} instruments produced no subscription key, which means a segment prefix is unknown")

    largest_instruments, instrument_evidence = await probe_instruments_per_connection(hsm_key, keys, logger)
    await asyncio.sleep(5)
    working_connections, refusal_reason, connection_evidence = await probe_connection_count(hsm_key, keys, ceiling, logger)

    if largest_instruments == 0 or working_connections == 0:
        logger.error("the probe could not establish either limit on the quote feed")
        return 1

    connection_count = max(1, working_connections - CONNECTION_SAFETY_MARGIN)
    instruments_per_connection = int(largest_instruments * INSTRUMENT_SAFETY_FRACTION)

    print()
    print("=" * 78)
    print("  quote feed")
    print(f"  largest subscription honoured on one connection : {largest_instruments:,}")
    print(f"  simultaneous connections that served data       : {working_connections}")
    print(f"  stopped because                                 : {refusal_reason or 'the ceiling was reached'}")
    print()
    print(f"  recommended connection_count                    : {connection_count}  (measured minus {CONNECTION_SAFETY_MARGIN})")
    print(f"  recommended instruments_per_connection          : {instruments_per_connection:,}  ({INSTRUMENT_SAFETY_FRACTION:.0%} of measured)")
    print(f"  that covers                                     : {connection_count * instruments_per_connection:,} instruments")
    print(f"  the live universe needs                         : {len(keys):,}")
    print(f"  Fyers documents                                 : 1 connection x 5,000 instruments")
    print("=" * 78)

    if store:
        document = write_capacity(
            BROKER_NAME,
            connection_count,
            instruments_per_connection,
            refusal_reason,
            instrument_evidence + connection_evidence,
            feed_name=MARKET_FEED,
        )
        print(f"\nstored in MongoDB stream_capacity under {MARKET_FEED}, measured_at {document['measured_at']}")

    if not include_tick_by_tick:
        return 0

    await asyncio.sleep(5)
    authorization = authorization_header_value(application_identifier, access_token)
    largest_symbols, depth_refusal, depth_evidence = await probe_tick_by_tick(authorization, instruments, logger)

    print()
    print("=" * 78)
    print("  tick-by-tick depth feed")
    print(f"  largest subscription honoured on one connection : {largest_symbols}")
    print(f"  stopped because                                 : {depth_refusal or 'the candidates were exhausted'}")
    print(f"  Fyers documents                                 : 3 connections x {DOCUMENTED_SYMBOLS_PER_CONNECTION} symbols")
    print("=" * 78)

    if store and largest_symbols:
        document = write_capacity(
            BROKER_NAME,
            TICK_BY_TICK_CONNECTION_COUNT,
            largest_symbols,
            depth_refusal,
            depth_evidence,
            feed_name=TICK_BY_TICK_FEED,
        )
        print(f"\nstored in MongoDB stream_capacity under {TICK_BY_TICK_FEED}, measured_at {document['measured_at']}")
    return 0


def main():
    """
    Parse the command line and run the capacity probe.

    Returns:
        None.

    Raises:
        SystemExit: Always, with the probe's exit status.
    """
    parser = argparse.ArgumentParser(description="Measure Fyers' real websocket limits.")
    parser.add_argument("--ceiling", type=int, default=CONNECTION_CEILING, help="Largest number of connections to attempt.")
    parser.add_argument("--no-store", action="store_true", help="Report the measurement without recording it.")
    parser.add_argument("--skip-tick-by-tick", action="store_true", help="Measure only the quote feed.")
    arguments = parser.parse_args()

    for feed_name in (MARKET_FEED, TICK_BY_TICK_FEED):
        previous = read_capacity(BROKER_NAME, feed_name)
        if previous is not None:
            print(f"previously measured on {feed_name}: {previous['connection_count']} connections x {previous['instruments_per_connection']:,} instruments, at {previous['measured_at']}")
    print()

    raise SystemExit(asyncio.run(run_probe(arguments.ceiling, not arguments.no_store, not arguments.skip_tick_by_tick)))


if __name__ == "__main__":
    main()
