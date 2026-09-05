"""
Measures how much Dhan's websockets actually allow, rather than what they document.

Dhan's documentation says five connections and three thousand instruments on the live feed, fifty instruments on a twenty level depth socket, and one instrument on a two hundred level depth socket. The live feed numbers, like Zerodha's, are believed to be lower bounds rather than enforced limits, so the real ones have to be established by trying.

Three things are measured. How many instruments one live feed connection will genuinely serve, how many connections can be open at once across the live feed and the depth sockets together, and how much one twenty level depth socket will serve. Dhan's excess connection behaviour differs from Zerodha's in a way the probe must respect: it does not refuse the sixth connection, it evicts the oldest healthy one with disconnect reason 805, so the probe watches its earlier connections for that eviction and counts the survivors as the answer.

The measurement leans on the same property Zerodha's does: the feed should send a snapshot of every subscribed instrument when a subscription is accepted. Whether Dhan really does, through prev close packets on subscribe, is one of the open questions this probe settles on its first live run, and if it does not, the instrument count it measures bounds acceptance only and must be re-qualified during market hours.

Run with: python3 -m stream.dhan.capacity_probe
"""

import argparse
import asyncio
from datetime import datetime

from sqlalchemy import create_engine, text

from stream.capacity import read_capacity, write_capacity
from stream.dhan import depth_packets
from stream.dhan.connection import (
    DhanAuthenticationError,
    DhanConnection,
    DhanConnectionRefusedError,
)
from stream.dhan.credentials import websocket_credentials
from stream.dhan.depth_connection import DhanDepthConnection
from stream.dhan.packets import decode_frame
from stream.dhan.verify_stream import dhan_exchange_segment
from utilities.configuration import postgres_configuration
from utilities.logging import configure_logging

BROKER_NAME = "dhan"
MARKET_FEED = "market_feed"
TWENTY_DEPTH = "twenty_depth"

CONNECTION_CEILING = 40
CONNECTION_BASKET_SIZE = 200
CONNECTION_SAFETY_MARGIN = 1

INSTRUMENT_CANDIDATES = [
    5000,
    8000,
    10000,
    15000,
    20000,
]
INSTRUMENT_SAFETY_FRACTION = 0.8

TWENTY_DEPTH_INSTRUMENTS = 50
TWO_HUNDRED_DEPTH_INSTRUMENTS = 1

SNAPSHOT_PATIENCE_SECONDS = 120.0
SNAPSHOT_POLL_SECONDS = 0.4


def live_instrument_pairs():
    """
    Read every distinct (exchange segment, security id) pair that is worth subscribing to today.

    Three filters matter and all change the answer. Expired contracts are excluded because they will never tick and would make the probe look as though capacity had been consumed by instruments that produce nothing. Segments Dhan does not feed, indexes on BSE and everything on NCDEX, are dropped because no subscription can carry them. Pairs are de-duplicated because one Dhan security id can be mapped to more than one instrument identity, so the mapping table returns it more than once; subscribing to the same instrument twice wastes a slot and makes a complete snapshot look incomplete.

    Returns:
        list[tuple]: Distinct (exchange_segment, security_id) pairs, sorted, from the most recent mapping.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the instrument tables cannot be read.
    """
    engine = create_engine(postgres_configuration["connection_string"])
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT DISTINCT b.broker_token, m.exchange, m.segment "
            "FROM instruments.broker_mappings b "
            "JOIN instruments.master m ON m.instrument_id = b.instrument_id "
            "WHERE b.broker = 'dhan' "
            "  AND b.mapping_date = (SELECT max(mapping_date) FROM instruments.broker_mappings WHERE broker = 'dhan') "
            "  AND (m.expiry_date IS NULL OR m.expiry_date > CURRENT_DATE)"
        )).all()

    pairs = set()
    for broker_token, master_exchange, master_segment in rows:
        exchange_segment = dhan_exchange_segment(master_exchange, master_segment)
        if exchange_segment is not None:
            pairs.add((exchange_segment, int(broker_token)))
    return sorted(pairs)


class SnapshotCollector:
    """
    Collects the instruments a connection actually delivers, so a truncated subscription can be seen.

    Attributes:
        wanted (set): The (exchange_segment, security_id) pairs that were subscribed to.
        seen (set): The pairs that have arrived.
        frames (int): Binary frames carrying data that have arrived.
        bytes_received (int): Total bytes of those frames.
    """

    def __init__(self, instrument_pairs):
        """
        Prepare a collector for one subscription.

        Args:
            instrument_pairs (list[tuple]): The (exchange_segment, security_id) pairs being subscribed to.

        Returns:
            None.
        """
        self.wanted = set(instrument_pairs)
        self.seen = set()
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
        if len(frame) < 8:
            return
        self.frames = self.frames + 1
        self.bytes_received = self.bytes_received + len(frame)
        for tick in decode_frame(frame, datetime.now()):
            self.seen.add((tick["exchange_segment"], tick["security_id"]))

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


class DepthSectionCollector:
    """
    Collects the depth sections a twenty level depth socket actually delivers.

    Attributes:
        wanted (set): The (exchange_segment, security_id) pairs that were subscribed to.
        seen (set): The pairs that have arrived, from either a bid or an ask section.
        frames (int): Binary frames carrying data that have arrived.
        sections (int): Bid and ask sections decoded in total.
        rows (int): Individual depth rows decoded in total.
        bytes_received (int): Total bytes of those frames.
    """

    def __init__(self, instrument_pairs):
        """
        Prepare a collector for one depth subscription.

        Args:
            instrument_pairs (list[tuple]): The (exchange_segment, security_id) pairs being subscribed to.

        Returns:
            None.
        """
        self.wanted = set(instrument_pairs)
        self.seen = set()
        self.frames = 0
        self.sections = 0
        self.rows = 0
        self.bytes_received = 0

    def on_frame(self, arrival_time_nanoseconds, frame):
        """
        Record whatever instruments a depth frame carried.

        Args:
            arrival_time_nanoseconds (int): When the frame was read, which this collector does not use.
            frame (bytes): The frame as received.

        Returns:
            None.
        """
        if len(frame) < 12:
            return
        self.frames = self.frames + 1
        self.bytes_received = self.bytes_received + len(frame)
        for tick in depth_packets.decode_frame(frame, 20, datetime.now()):
            self.seen.add((tick["exchange_segment"], tick["security_id"]))
            self.sections = self.sections + 1
            self.rows = self.rows + len(tick.get("bid_prices") or []) + len(tick.get("ask_prices") or [])

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


async def open_and_collect(client_id, access_token, instrument_pairs, patience_seconds):
    """
    Open one live feed connection, subscribe, and wait for the snapshot to arrive in full.

    Args:
        client_id (str): The Dhan client identifier.
        access_token (str): An access token issued today.
        instrument_pairs (list[tuple]): The (exchange_segment, security_id) pairs to subscribe to in full mode.
        patience_seconds (float): How long to wait for every instrument to arrive before giving up.

    Returns:
        tuple: A (collector, connection, task, stop_event, refusal) tuple, where refusal is None when the connection was accepted and a string describing the refusal otherwise. The connection is left open so the caller can decide when to close it.

    Raises:
        DhanAuthenticationError: If Dhan rejected the credentials.
    """
    collector = SnapshotCollector(instrument_pairs)
    feed_connection = DhanConnection(
        client_id=client_id,
        access_token=access_token,
        instruments=instrument_pairs,
        on_frame=collector.on_frame,
        mode="full",
        maximum_reconnect_attempts=0,
    )
    stop_event = asyncio.Event()
    task = asyncio.create_task(feed_connection.run(stop_event))

    refusal = None
    waited = 0.0
    while waited < patience_seconds:
        await asyncio.sleep(SNAPSHOT_POLL_SECONDS)
        waited = waited + SNAPSHOT_POLL_SECONDS
        if collector.is_complete():
            break
        if task.done():
            exception = task.exception()
            if isinstance(exception, DhanAuthenticationError):
                raise exception
            if exception is not None:
                refusal = f"{type(exception).__name__}: {exception}"
            break

    return (collector, feed_connection, task, stop_event, refusal)


async def open_depth_and_collect(client_id, access_token, depth_level, instrument_pairs, patience_seconds):
    """
    Open one twenty level depth connection, subscribe, and wait for the snapshot to arrive in full.

    Args:
        client_id (str): The Dhan client identifier.
        access_token (str): An access token issued today.
        depth_level (int): The depth level to subscribe to, always 20 for the probe.
        instrument_pairs (list[tuple]): The (exchange_segment, security_id) pairs to subscribe.
        patience_seconds (float): How long to wait for every instrument to arrive before giving up.

    Returns:
        tuple: A (collector, connection, task, stop_event, refusal) tuple, where refusal is None when the connection was accepted and a string describing the refusal otherwise. The connection is left open so the caller can decide when to close it.

    Raises:
        DhanAuthenticationError: If Dhan rejected the credentials.
    """
    collector = DepthSectionCollector(instrument_pairs)
    depth_connection = DhanDepthConnection(
        depth_level=depth_level,
        client_id=client_id,
        access_token=access_token,
        instruments=instrument_pairs,
        on_frame=collector.on_frame,
        maximum_reconnect_attempts=0,
    )
    stop_event = asyncio.Event()
    task = asyncio.create_task(depth_connection.run(stop_event))

    refusal = None
    waited = 0.0
    while waited < patience_seconds:
        await asyncio.sleep(SNAPSHOT_POLL_SECONDS)
        waited = waited + SNAPSHOT_POLL_SECONDS
        if collector.is_complete():
            break
        if task.done():
            exception = task.exception()
            if isinstance(exception, DhanAuthenticationError):
                raise exception
            if exception is not None:
                refusal = f"{type(exception).__name__}: {exception}"
            break

    return (collector, depth_connection, task, stop_event, refusal)


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


async def probe_instruments_per_connection(client_id, access_token, pairs, logger):
    """
    Find the largest number of instruments one live feed connection will serve in full.

    Each candidate gets a fresh connection, because a subscription added to an existing one would not distinguish a connection that accepts many instruments from one that accepts many subscriptions.

    Args:
        client_id (str): The Dhan client identifier.
        access_token (str): An access token issued today.
        pairs (list[tuple]): Distinct (exchange_segment, security_id) pairs to draw candidates from.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (largest_complete, evidence) pair, where evidence is a list of dicts describing each candidate tried.

    Raises:
        DhanAuthenticationError: If Dhan rejected the credentials.
    """
    evidence = []
    largest_complete = 0

    candidates = []
    for candidate in INSTRUMENT_CANDIDATES:
        if candidate < len(pairs):
            candidates.append(candidate)
    candidates.append(len(pairs))

    for candidate in candidates:
        chosen = pairs[:candidate]
        collector, feed_connection, task, stop_event, refusal = await open_and_collect(
            client_id, access_token, chosen, SNAPSHOT_PATIENCE_SECONDS
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


async def probe_connection_count(client_id, access_token, pairs, ceiling, logger):
    """
    Find how many connections can be open at once, holding every earlier one open while testing the next.

    Earlier connections are held rather than closed because Dhan evicts the oldest healthy connection when one too many arrives, and only a connection that stays open long enough can be the victim. When the victim dies with reason 805 the survivors are the true limit, so the probe counts them rather than treating the eviction as a failure of the connection that caused it.

    Args:
        client_id (str): The Dhan client identifier.
        access_token (str): An access token issued today.
        pairs (list[tuple]): Distinct (exchange_segment, security_id) pairs to build a small basket for each connection from.
        ceiling (int): Stop at this many connections even if none has been evicted, so a runaway probe cannot look like an attack on the broker.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (working_connections, refusal_reason, evidence) triple.

    Raises:
        DhanAuthenticationError: If Dhan rejected the credentials.
    """
    evidence = []
    open_probes = []
    refusal_reason = None
    working = None

    for number in range(ceiling):
        basket = pairs[number * CONNECTION_BASKET_SIZE:(number + 1) * CONNECTION_BASKET_SIZE]
        collector, feed_connection, task, stop_event, refusal = await open_and_collect(
            client_id, access_token, basket, 12.0
        )
        complete = collector.is_complete()
        earlier_healthy = 0
        for probe in open_probes:
            if probe[1].connected and not probe[2].done():
                earlier_healthy = earlier_healthy + 1

        evidence.append({
            "connection_number": number + 1,
            "delivered": collector.delivered(),
            "basket_size": len(basket),
            "outcome": "complete" if complete else ("refused" if refusal else "incomplete"),
            "earlier_connections_still_healthy": earlier_healthy,
            "detail": refusal,
        })
        logger.info(
            f"connection {number + 1}: {'serving' if complete else 'NOT serving'}, "
            f"{earlier_healthy} of {len(open_probes)} earlier connections still healthy"
            f"{' - ' + refusal if refusal else ''}"
        )

        if refusal or not complete:
            refusal_reason = refusal or "snapshot_not_delivered"
            working = earlier_healthy
            await close_probe(task, stop_event)
            break
        if earlier_healthy != len(open_probes):
            refusal_reason = "earlier_connection_evicted"
            working = earlier_healthy + 1
            await close_probe(task, stop_event)
            break

        open_probes.append((collector, feed_connection, task, stop_event))
        await asyncio.sleep(1.0)

    if working is None:
        working = len(open_probes)
    for probe in open_probes:
        await close_probe(probe[2], probe[3])

    return (working, refusal_reason, evidence)


async def probe_depth_sockets(client_id, access_token, pairs, logger):
    """
    Measure what the depth sockets allow while the live feed holds one connection open.

    Three things are observed, in one pass, with a live feed connection held open throughout so the answer reflects the shared connection pool rather than an idle account. Whether a fifty instrument twenty level socket is honoured in full, whether a two hundred level socket carrying its single instrument coexists with both, and whether the twenty level socket keeps serving once the two hundred level socket has joined.

    Args:
        client_id (str): The Dhan client identifier.
        access_token (str): An access token issued today.
        pairs (list[tuple]): Distinct (exchange_segment, security_id) pairs to fill the depth sockets from.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (twenty_depth_delivered, evidence) pair, where twenty_depth_delivered is how many of the fifty instruments the twenty level socket served.

    Raises:
        DhanAuthenticationError: If Dhan rejected the credentials.
    """
    evidence = []

    live_collector, live_connection, live_task, live_stop, live_refusal = await open_and_collect(
        client_id, access_token, pairs[:CONNECTION_BASKET_SIZE], 12.0
    )
    if live_refusal:
        logger.warning(f"the live feed connection was refused before the depth probes: {live_refusal}")
    evidence.append({
        "stage": "live_feed_held_open",
        "delivered": live_collector.delivered(),
        "outcome": "complete" if live_collector.is_complete() else ("refused" if live_refusal else "incomplete"),
        "detail": live_refusal,
    })

    twenty_pairs = pairs[CONNECTION_BASKET_SIZE:CONNECTION_BASKET_SIZE + TWENTY_DEPTH_INSTRUMENTS]
    twenty_collector, twenty_connection, twenty_task, twenty_stop, twenty_refusal = await open_depth_and_collect(
        client_id, access_token, 20, twenty_pairs, SNAPSHOT_PATIENCE_SECONDS
    )
    twenty_complete = twenty_collector.is_complete()
    evidence.append({
        "stage": "twenty_depth_socket",
        "instrument_count": len(twenty_pairs),
        "delivered": twenty_collector.delivered(),
        "frames": twenty_collector.frames,
        "sections": twenty_collector.sections,
        "rows": twenty_collector.rows,
        "outcome": "complete" if twenty_complete else ("refused" if twenty_refusal else "incomplete"),
        "detail": twenty_refusal,
    })
    logger.info(
        f"twenty depth socket: {twenty_collector.delivered()} of {len(twenty_pairs)} instruments delivered, "
        f"{twenty_collector.sections} sections in {twenty_collector.frames} frames"
        f"{' - ' + twenty_refusal if twenty_refusal else ''}"
    )

    two_hundred_pairs = pairs[CONNECTION_BASKET_SIZE + TWENTY_DEPTH_INSTRUMENTS:CONNECTION_BASKET_SIZE + TWENTY_DEPTH_INSTRUMENTS + TWO_HUNDRED_DEPTH_INSTRUMENTS]
    two_hundred_collector = None
    two_hundred_task = None
    two_hundred_stop = None
    two_hundred_refusal = None
    if twenty_complete:
        two_hundred_collector, two_hundred_connection, two_hundred_task, two_hundred_stop, two_hundred_refusal = await open_depth_and_collect(
            client_id, access_token, 200, two_hundred_pairs, 12.0
        )
        evidence.append({
            "stage": "two_hundred_depth_socket",
            "instrument_count": len(two_hundred_pairs),
            "delivered": two_hundred_collector.delivered(),
            "outcome": "complete" if two_hundred_collector.is_complete() else ("refused" if two_hundred_refusal else "incomplete"),
            "detail": two_hundred_refusal,
        })
        logger.info(
            f"two hundred depth socket: {'accepted while live and twenty depth held open' if two_hundred_collector.connected else 'NOT accepted'}"
            f"{' - ' + two_hundred_refusal if two_hundred_refusal else ''}"
        )

        twenty_still_serving = twenty_connection.connected and not twenty_task.done()
        evidence.append({
            "stage": "twenty_depth_after_two_hundred_joined",
            "outcome": "complete" if twenty_still_serving else "dropped",
        })

    twenty_delivered = twenty_collector.delivered() if not twenty_refusal else 0
    for task, stop_event in [(live_task, live_stop), (twenty_task, twenty_stop), (two_hundred_task, two_hundred_stop)]:
        if task is not None:
            await close_probe(task, stop_event)

    return (twenty_delivered, evidence)

async def run_probe(ceiling, store):
    """
    Measure the live feed and the depth sockets, and optionally record the results.

    The live feed and the twenty level depth socket are measured and stored as separate documents, because they are capped differently even though they draw on one connection pool. The two hundred level socket takes one connection for one instrument by design, so it contributes no measurement of its own and its coexistence evidence rides on the twenty depth document.

    Args:
        ceiling (int): The largest number of connections to attempt.
        store (bool): Whether to write the measurements to MongoDB.

    Returns:
        int: 0 when the probe completed, 1 when it could not measure anything.

    Raises:
        DhanAuthenticationError: If Dhan rejected the credentials.
    """
    logger = configure_logging("stream_dhan_capacity_probe")
    client_id, access_token = websocket_credentials()
    pairs = live_instrument_pairs()
    logger.info(f"probing with {len(pairs)} distinct live (segment, security id) pairs")

    largest_instruments, instrument_evidence = await probe_instruments_per_connection(client_id, access_token, pairs, logger)
    await asyncio.sleep(5)
    working_connections, refusal_reason, connection_evidence = await probe_connection_count(client_id, access_token, pairs, ceiling, logger)
    await asyncio.sleep(5)
    twenty_depth_delivered, depth_evidence = await probe_depth_sockets(client_id, access_token, pairs, logger)

    if largest_instruments == 0 or working_connections == 0:
        logger.error("the probe could not establish either live feed limit")
        return 1

    connection_count = max(1, working_connections - CONNECTION_SAFETY_MARGIN)
    instruments_per_connection = int(largest_instruments * INSTRUMENT_SAFETY_FRACTION)

    print()
    print("=" * 78)
    print(f"  largest subscription honoured on one connection : {largest_instruments:,}")
    print(f"  simultaneous connections that served data       : {working_connections}")
    print(f"  stopped because                                 : {refusal_reason or 'the ceiling was reached'}")
    print()
    print(f"  recommended connection_count                    : {connection_count}  (measured minus {CONNECTION_SAFETY_MARGIN})")
    print(f"  recommended instruments_per_connection          : {instruments_per_connection:,}  ({INSTRUMENT_SAFETY_FRACTION:.0%} of measured)")
    print(f"  that covers                                     : {connection_count * instruments_per_connection:,} instruments")
    print(f"  the live universe needs                         : {len(pairs):,}")
    print()
    print(f"  twenty depth socket, instruments delivered      : {twenty_depth_delivered} of {TWENTY_DEPTH_INSTRUMENTS}")
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
        print(f"\nstored in MongoDB stream_capacity as feed {MARKET_FEED}, measured_at {document['measured_at']}")
        depth_document = write_capacity(
            BROKER_NAME,
            1,
            twenty_depth_delivered,
            refusal_reason,
            depth_evidence,
            feed_name=TWENTY_DEPTH,
        )
        print(f"stored in MongoDB stream_capacity as feed {TWENTY_DEPTH}, measured_at {depth_document['measured_at']}")
    return 0


def main():
    """
    Parse the command line and run the capacity probe.

    Returns:
        None.

    Raises:
        SystemExit: Always, with the probe's exit status.
    """
    parser = argparse.ArgumentParser(description="Measure Dhan's real websocket limits.")
    parser.add_argument("--ceiling", type=int, default=CONNECTION_CEILING, help="Largest number of connections to attempt.")
    parser.add_argument("--no-store", action="store_true", help="Report the measurements without recording them.")
    arguments = parser.parse_args()

    previous = read_capacity(BROKER_NAME)
    if previous is not None:
        print(f"previously measured: {previous['connection_count']} connections x {previous['instruments_per_connection']:,} instruments, at {previous['measured_at']}")
        print()

    raise SystemExit(asyncio.run(run_probe(arguments.ceiling, not arguments.no_store)))


if __name__ == "__main__":
    main()
