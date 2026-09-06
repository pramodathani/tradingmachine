"""
Measures how much Flattrade's websocket actually allows, rather than what it documents.

Flattrade documents no connection limit and no instrument limit at all, which makes it the one broker whose capacity cannot even be bounded by its own marketing. The only thing the wire documents is that subscriptions are not retained across connections, so every probe connection re-subscribes on connect and the snapshot that follows is what the probe measures.

Three things are measured. How many instruments one touchline connection will genuinely serve in full, how many connections can be open at once with every earlier one held open, and what one depth connection serves while a touchline connection is held open. The protocol's one observed way of saying no is the connect acknowledgement answering Not_Ok on a session that is not the first, which the connection driver raises as FlattradeConnectionRefusedError; a probe that sees it counts the earlier survivors as the answer.

The measurement leans on the same property the other brokers' probes lean on: the feed should send a full snapshot of every subscribed instrument when a subscription is accepted. That Flattrade does this, one tk or dk per scrip, is itself one of the open questions this probe settles on its first live run.

Run with: python3 -m stream.flattrade.capacity_probe
"""

import argparse
import asyncio
from datetime import datetime

from sqlalchemy import create_engine, text

from stream.capacity import read_capacity, write_capacity
from stream.flattrade import packets
from stream.flattrade.connection import (
    FlattradeAuthenticationError,
    FlattradeConnection,
    MODE_DEPTH,
    MODE_TOUCHLINE,
)
from stream.flattrade.credentials import websocket_credentials
from stream.flattrade.verify_stream import flattrade_exchange_code
from utilities.configuration import postgres_configuration
from utilities.logging import configure_logging

BROKER_NAME = "flattrade"
MARKET_FEED = "market_feed"
FIVE_DEPTH = "five_depth"

CONNECTION_CEILING = 20
CONNECTION_BASKET_SIZE = 200

INSTRUMENT_CANDIDATES = [
    5000,
    10000,
    20000,
    40000,
    80000,
]
INSTRUMENT_SAFETY_FRACTION = 0.8

FIVE_DEPTH_INSTRUMENTS = 500

SNAPSHOT_PATIENCE_SECONDS = 120.0
SNAPSHOT_POLL_SECONDS = 0.4


def live_instrument_keys():
    """
    Read every distinct exchange and token pair that is worth subscribing to today, as wire keys.

    The filters matter and all change the answer. Expired contracts are excluded because they will never tick and would make the probe look as though capacity had been consumed by instruments that produce nothing. Segments Flattrade does not feed, the exchange traded funds, investment trusts and the uncategorised remainder, are dropped because no subscription can carry them. Keys are de-duplicated on the "EXCHANGE|TOKEN" string itself, because Flattrade's scrip master carries more duplicate tokens than any other broker's and subscribing to the same key twice wastes a slot and makes a complete snapshot look incomplete.

    Returns:
        list[str]: Distinct instrument keys, sorted, from the most recent mapping.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the instrument tables cannot be read.
    """
    engine = create_engine(postgres_configuration["connection_string"])
    with engine.connect() as db_connection:
        rows = db_connection.execute(text(
            "SELECT b.broker_token, m.exchange, m.segment "
            "FROM instruments.broker_mappings b "
            "JOIN instruments.master m ON m.instrument_id = b.instrument_id "
            "WHERE b.broker = 'flattrade' "
            "  AND b.mapping_date = (SELECT max(mapping_date) FROM instruments.broker_mappings WHERE broker = 'flattrade') "
            "  AND (m.expiry_date IS NULL OR m.expiry_date > CURRENT_DATE)"
        )).all()

    keys = set()
    for broker_token, master_exchange, master_segment in rows:
        exchange_code = flattrade_exchange_code(master_exchange, master_segment)
        if exchange_code is not None:
            keys.add(f"{exchange_code}|{broker_token}")
    return sorted(keys)


class SnapshotCollector:
    """
    Collects the instruments a connection actually delivers, so a truncated subscription can be seen.

    Attributes:
        wanted (set): The (exchange, token) pairs that were subscribed to.
        seen (set): The pairs that have arrived.
        frames (int): Frames carrying market data that have arrived.
        bytes_received (int): Total bytes of those frames.
    """

    def __init__(self, instrument_keys):
        """
        Prepare a collector for one subscription.

        Args:
            instrument_keys (list[str]): The "EXCHANGE|TOKEN" keys being subscribed to.

        Returns:
            None.
        """
        self.wanted = set()
        for key in instrument_keys:
            exchange, token = key.split("|", 1)
            self.wanted.add((exchange, token))
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
        self.frames = self.frames + 1
        self.bytes_received = self.bytes_received + len(frame)
        for tick in packets.decode_frame(frame, datetime.now()):
            self.seen.add((tick["exchange"], tick["token"]))

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


async def open_and_collect(uid, access_token, instrument_keys, mode, patience_seconds):
    """
    Open one connection, subscribe, and wait for the snapshot to arrive in full.

    Args:
        uid (str): The Flattrade user identifier.
        access_token (str): An access token issued today.
        instrument_keys (list[str]): The "EXCHANGE|TOKEN" keys to subscribe to.
        mode (str): The feed mode to subscribe in, MODE_TOUCHLINE or MODE_DEPTH.
        patience_seconds (float): How long to wait for every instrument to arrive before giving up.

    Returns:
        tuple: A (collector, connection, task, stop_event, refusal) tuple, where refusal is None when the connection was accepted and a string describing the refusal otherwise. The connection is left open so the caller can decide when to close it.

    Raises:
        FlattradeAuthenticationError: If Flattrade rejected the credentials outright.
    """
    collector = SnapshotCollector(instrument_keys)
    feed_connection = FlattradeConnection(
        uid=uid,
        access_token=access_token,
        instruments=instrument_keys,
        on_frame=collector.on_frame,
        mode=mode,
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
            if isinstance(exception, FlattradeAuthenticationError):
                raise exception
            if exception is not None:
                refusal = f"{type(exception).__name__}: {exception}"
            break

    return (collector, feed_connection, task, stop_event, refusal)


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


async def probe_instruments_per_connection(uid, access_token, keys, logger):
    """
    Find the largest number of instruments one touchline connection will serve in full.

    Each candidate gets a fresh connection, because a subscription added to an existing one would not distinguish a connection that accepts many instruments from one that accepts many subscriptions.

    Args:
        uid (str): The Flattrade user identifier.
        access_token (str): An access token issued today.
        keys (list[str]): Distinct instrument keys to draw candidates from.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (largest_complete, evidence) pair, where evidence is a list of dicts describing each candidate tried.

    Raises:
        FlattradeAuthenticationError: If Flattrade rejected the credentials.
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
        collector, feed_connection, task, stop_event, refusal = await open_and_collect(
            uid, access_token, chosen, MODE_TOUCHLINE, SNAPSHOT_PATIENCE_SECONDS
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


async def probe_connection_count(uid, access_token, keys, ceiling, logger):
    """
    Find how many connections can be open at once, holding every earlier one open while testing the next.

    Earlier connections are held rather than closed because a limit on simultaneous connections can only be seen by connections that stay open, and because the one refusal the protocol has been observed to send, a Not_Ok connect acknowledgement on a later session, could also take an earlier connection down with it. When an earlier connection dies the survivors are the true limit, so the probe counts them rather than treating the death as a failure of the connection that caused it.

    Args:
        uid (str): The Flattrade user identifier.
        access_token (str): An access token issued today.
        keys (list[str]): Distinct instrument keys to build a small basket for each connection from.
        ceiling (int): Stop at this many connections even if none has been refused, so a runaway probe cannot look like an attack on the broker.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (working_connections, refusal_reason, evidence) triple.

    Raises:
        FlattradeAuthenticationError: If Flattrade rejected the credentials.
    """
    evidence = []
    open_probes = []
    refusal_reason = None
    working = None

    for number in range(ceiling):
        basket = keys[number * CONNECTION_BASKET_SIZE:(number + 1) * CONNECTION_BASKET_SIZE]
        collector, feed_connection, task, stop_event, refusal = await open_and_collect(
            uid, access_token, basket, MODE_TOUCHLINE, 12.0
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
            refusal_reason = "earlier_connection_died"
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


async def probe_depth_feed(uid, access_token, keys, logger):
    """
    Measure what one depth connection serves while a touchline connection is held open.

    The touchline connection is held throughout so the answer reflects an account that is already streaming rather than an idle one. The depth basket is larger than the touchline basket per connection because a depth snapshot is bigger, not smaller, and the interesting question is whether the same connection carries a depth subscription of realistic size.

    Args:
        uid (str): The Flattrade user identifier.
        access_token (str): An access token issued today.
        keys (list[str]): Distinct instrument keys to fill the depth subscription from.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (depth_delivered, evidence) pair, where depth_delivered is how many of the depth instruments the depth connection served.

    Raises:
        FlattradeAuthenticationError: If Flattrade rejected the credentials.
    """
    evidence = []

    touchline_keys = keys[:CONNECTION_BASKET_SIZE]
    touchline_collector, touchline_connection, touchline_task, touchline_stop, touchline_refusal = await open_and_collect(
        uid, access_token, touchline_keys, MODE_TOUCHLINE, 12.0
    )
    if touchline_refusal:
        logger.warning(f"the touchline connection was refused before the depth probe: {touchline_refusal}")
    evidence.append({
        "stage": "touchline_held_open",
        "delivered": touchline_collector.delivered(),
        "outcome": "complete" if touchline_collector.is_complete() else ("refused" if touchline_refusal else "incomplete"),
        "detail": touchline_refusal,
    })

    depth_keys = keys[CONNECTION_BASKET_SIZE:CONNECTION_BASKET_SIZE + FIVE_DEPTH_INSTRUMENTS]
    depth_collector, depth_connection, depth_task, depth_stop, depth_refusal = await open_and_collect(
        uid, access_token, depth_keys, MODE_DEPTH, SNAPSHOT_PATIENCE_SECONDS
    )
    depth_complete = depth_collector.is_complete()
    evidence.append({
        "stage": "five_depth_connection",
        "instrument_count": len(depth_keys),
        "delivered": depth_collector.delivered(),
        "frames": depth_collector.frames,
        "bytes_received": depth_collector.bytes_received,
        "outcome": "complete" if depth_complete else ("refused" if depth_refusal else "incomplete"),
        "detail": depth_refusal,
    })
    logger.info(
        f"five depth connection: {depth_collector.delivered()} of {len(depth_keys)} instruments delivered, "
        f"{depth_collector.frames} frames, {depth_collector.bytes_received:,} bytes"
        f"{' - ' + depth_refusal if depth_refusal else ''}"
    )

    touchline_still_serving = touchline_connection.connected and not touchline_task.done()
    evidence.append({
        "stage": "touchline_after_depth_joined",
        "outcome": "complete" if touchline_still_serving else "dropped",
    })

    depth_delivered = depth_collector.delivered() if not depth_refusal else 0
    for task, stop_event in [(touchline_task, touchline_stop), (depth_task, depth_stop)]:
        await close_probe(task, stop_event)

    return (depth_delivered, evidence)


async def run_probe(ceiling, store):
    """
    Measure the touchline and depth feeds, and optionally record the results.

    Args:
        ceiling (int): The largest number of connections to attempt.
        store (bool): Whether to write the measurements to MongoDB.

    Returns:
        int: 0 when the probe completed, 1 when it could not measure anything.

    Raises:
        FlattradeAuthenticationError: If Flattrade rejected the credentials.
    """
    logger = configure_logging("stream_flattrade_capacity_probe")
    uid, access_token = websocket_credentials()
    keys = live_instrument_keys()
    logger.info(f"probing with {len(keys)} distinct instrument keys")

    largest_instruments, instrument_evidence = await probe_instruments_per_connection(uid, access_token, keys, logger)
    await asyncio.sleep(5)
    working_connections, refusal_reason, connection_evidence = await probe_connection_count(uid, access_token, keys, ceiling, logger)
    await asyncio.sleep(5)
    depth_delivered, depth_evidence = await probe_depth_feed(uid, access_token, keys, logger)

    if largest_instruments == 0 or working_connections == 0:
        logger.error("the probe could not establish either touchline limit")
        return 1

    connection_count = max(1, working_connections - 1)
    instruments_per_connection = int(largest_instruments * INSTRUMENT_SAFETY_FRACTION)

    print()
    print("=" * 78)
    print(f"  largest subscription honoured on one connection : {largest_instruments:,}")
    print(f"  simultaneous connections that served data       : {working_connections}")
    print(f"  stopped because                                 : {refusal_reason or 'the ceiling was reached'}")
    print()
    print(f"  recommended connection_count                    : {connection_count}  (measured minus 1)")
    print(f"  recommended instruments_per_connection          : {instruments_per_connection:,}  ({INSTRUMENT_SAFETY_FRACTION:.0%} of measured)")
    print(f"  that covers                                     : {connection_count * instruments_per_connection:,} instruments")
    print(f"  the live universe needs                         : {len(keys):,}")
    print()
    print(f"  five depth connection, instruments delivered    : {depth_delivered} of {FIVE_DEPTH_INSTRUMENTS}")
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
            depth_delivered,
            refusal_reason,
            depth_evidence,
            feed_name=FIVE_DEPTH,
        )
        print(f"stored in MongoDB stream_capacity as feed {FIVE_DEPTH}, measured_at {depth_document['measured_at']}")
    return 0


def main():
    """
    Parse the command line and run the capacity probe.

    Returns:
        None.

    Raises:
        SystemExit: Always, with the probe's exit status.
    """
    parser = argparse.ArgumentParser(description="Measure Flattrade's real websocket limits.")
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