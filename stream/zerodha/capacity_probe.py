"""
Measures how much Zerodha's websocket actually allows, rather than what it documents.

Zerodha's documentation says three connections per API key and three thousand instruments on each. Neither number matches what the service enforces, and since the whole universe has to be covered, the real limits have to be established by trying.

Two things are measured. How many instruments one connection will genuinely serve, and how many connections can be open at once. Both are found by increasing until the answer stops being yes, and both stop at the first refusal rather than probing around it.

The measurement leans on a convenient property of the service: Zerodha sends a snapshot of every subscribed instrument as soon as it accepts a subscription. So a subscription that was quietly truncated shows up immediately as instruments missing from the snapshot, and the probe works outside market hours, when nothing would otherwise tick.

Run with: python3 -m stream.zerodha.capacity_probe
"""

import argparse
import asyncio
from datetime import datetime

from sqlalchemy import create_engine, text

from stream.capacity import read_capacity, write_capacity
from stream.zerodha.connection import (
    ZerodhaAuthenticationError,
    ZerodhaConnection,
    ZerodhaConnectionRefusedError,
)
from stream.zerodha.credentials import websocket_credentials
from stream.zerodha.packets import decode_frame
from utilities.configuration import postgres_configuration
from utilities.logging import configure_logging

BROKER_NAME = "zerodha"

CONNECTION_CEILING = 40
CONNECTION_BASKET_SIZE = 200
CONNECTION_SAFETY_MARGIN = 2

INSTRUMENT_CANDIDATES = [
    5000,
    10000,
    20000,
    40000,
    80000,
]
INSTRUMENT_SAFETY_FRACTION = 0.8

SNAPSHOT_PATIENCE_SECONDS = 120.0
SNAPSHOT_POLL_SECONDS = 0.4


def live_instrument_tokens():
    """
    Read every distinct Zerodha instrument token that is worth subscribing to today.

    Two filters matter and both change the answer. Expired contracts are excluded because they will never tick and would make the probe look as though capacity had been consumed by instruments that produce nothing. Tokens are de-duplicated because one Zerodha token can be mapped to more than one instrument identity, so the mapping table returns it more than once; subscribing to the same token twice wastes a slot and, more confusingly, makes a complete snapshot look incomplete.

    Returns:
        list[int]: Distinct instrument tokens, sorted, from the most recent mapping.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the instrument tables cannot be read.
    """
    engine = create_engine(postgres_configuration["connection_string"])
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT DISTINCT b.broker_token "
            "FROM instruments.broker_mappings b "
            "JOIN instruments.master m ON m.instrument_id = b.instrument_id "
            "WHERE b.broker = 'zerodha' "
            "  AND b.mapping_date = (SELECT max(mapping_date) FROM instruments.broker_mappings WHERE broker = 'zerodha') "
            "  AND (m.expiry_date IS NULL OR m.expiry_date > CURRENT_DATE)"
        )).all()
    return sorted({int(row.broker_token) for row in rows})


class SnapshotCollector:
    """
    Collects the instruments a connection actually delivers, so a truncated subscription can be seen.

    Attributes:
        wanted (set): The instrument tokens that were subscribed to.
        seen (set): The instrument tokens that have arrived.
        frames (int): Binary frames carrying data that have arrived.
        bytes_received (int): Total bytes of those frames.
    """

    def __init__(self, instrument_tokens):
        """
        Prepare a collector for one subscription.

        Args:
            instrument_tokens (list[int]): The tokens that are being subscribed to.

        Returns:
            None.
        """
        self.wanted = set(instrument_tokens)
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
        if len(frame) < 2:
            return
        self.frames = self.frames + 1
        self.bytes_received = self.bytes_received + len(frame)
        for tick in decode_frame(frame, datetime.now()):
            self.seen.add(tick["instrument_token"])

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


async def open_and_collect(api_key, access_token, instrument_tokens, patience_seconds):
    """
    Open one connection, subscribe, and wait for the snapshot to arrive in full.

    Args:
        api_key (str): The Zerodha Kite Connect API key.
        access_token (str): An access token issued today.
        instrument_tokens (list[int]): The tokens to subscribe to in full mode.
        patience_seconds (float): How long to wait for every instrument to arrive before giving up.

    Returns:
        tuple: A (collector, connection, task, stop_event, refusal) tuple, where refusal is None when the connection was accepted and a string describing the refusal otherwise. The connection is left open so the caller can decide when to close it.

    Raises:
        ZerodhaAuthenticationError: If Zerodha rejected the credentials.
    """
    collector = SnapshotCollector(instrument_tokens)
    connection = ZerodhaConnection(
        api_key=api_key,
        access_token=access_token,
        instrument_tokens=instrument_tokens,
        on_frame=collector.on_frame,
        mode="full",
        maximum_reconnect_attempts=0,
    )
    stop_event = asyncio.Event()
    task = asyncio.create_task(connection.run(stop_event))

    refusal = None
    waited = 0.0
    while waited < patience_seconds:
        await asyncio.sleep(SNAPSHOT_POLL_SECONDS)
        waited = waited + SNAPSHOT_POLL_SECONDS
        if collector.is_complete():
            break
        if task.done():
            exception = task.exception()
            if isinstance(exception, ZerodhaAuthenticationError):
                raise exception
            if exception is not None:
                refusal = f"{type(exception).__name__}: {exception}"
            break

    return (collector, connection, task, stop_event, refusal)


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


async def probe_instruments_per_connection(api_key, access_token, tokens, logger):
    """
    Find the largest number of instruments one connection will serve in full.

    Each candidate gets a fresh connection, because a subscription added to an existing one would not distinguish a connection that accepts many instruments from one that accepts many subscriptions.

    Args:
        api_key (str): The Zerodha Kite Connect API key.
        access_token (str): An access token issued today.
        tokens (list[int]): Distinct instrument tokens to draw candidates from.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (largest_complete, evidence) pair, where evidence is a list of dicts describing each candidate tried.

    Raises:
        ZerodhaAuthenticationError: If Zerodha rejected the credentials.
    """
    evidence = []
    largest_complete = 0

    candidates = []
    for candidate in INSTRUMENT_CANDIDATES:
        if candidate < len(tokens):
            candidates.append(candidate)
    candidates.append(len(tokens))

    for candidate in candidates:
        chosen = tokens[:candidate]
        collector, connection, task, stop_event, refusal = await open_and_collect(
            api_key, access_token, chosen, SNAPSHOT_PATIENCE_SECONDS
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


async def probe_connection_count(api_key, access_token, tokens, ceiling, logger):
    """
    Find how many connections can be open at once, holding every earlier one open while testing the next.

    Earlier connections are held rather than closed because the question is how many the account supports simultaneously, and because a broker that starves an older connection when a new one arrives would otherwise go unnoticed.

    Args:
        api_key (str): The Zerodha Kite Connect API key.
        access_token (str): An access token issued today.
        tokens (list[int]): Distinct instrument tokens to build a small basket for each connection from.
        ceiling (int): Stop at this many connections even if none has been refused, so a runaway probe cannot look like an attack on the broker.
        logger (logging.Logger): Where to report progress.

    Returns:
        tuple: A (working_connections, refusal_reason, evidence) triple.

    Raises:
        ZerodhaAuthenticationError: If Zerodha rejected the credentials.
    """
    evidence = []
    open_probes = []
    refusal_reason = None

    for number in range(ceiling):
        basket = tokens[number * CONNECTION_BASKET_SIZE:(number + 1) * CONNECTION_BASKET_SIZE]
        collector, connection, task, stop_event, refusal = await open_and_collect(
            api_key, access_token, basket, 12.0
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

        open_probes.append((collector, connection, task, stop_event))
        await asyncio.sleep(1.0)

    working = len(open_probes)
    for probe in open_probes:
        await close_probe(probe[2], probe[3])

    return (working, refusal_reason, evidence)


async def run_probe(ceiling, store):
    """
    Measure both limits and optionally record the result.

    Args:
        ceiling (int): The largest number of connections to attempt.
        store (bool): Whether to write the measurement to MongoDB.

    Returns:
        int: 0 when the probe completed, 1 when it could not measure anything.

    Raises:
        ZerodhaAuthenticationError: If Zerodha rejected the credentials.
    """
    logger = configure_logging("stream_zerodha_capacity_probe")
    api_key, access_token = websocket_credentials()
    tokens = live_instrument_tokens()
    logger.info(f"probing with {len(tokens)} distinct live instrument tokens")

    largest_instruments, instrument_evidence = await probe_instruments_per_connection(api_key, access_token, tokens, logger)
    await asyncio.sleep(5)
    working_connections, refusal_reason, connection_evidence = await probe_connection_count(api_key, access_token, tokens, ceiling, logger)

    if largest_instruments == 0 or working_connections == 0:
        logger.error("the probe could not establish either limit")
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
    print(f"  the live universe needs                         : {len(tokens):,}")
    print("=" * 78)

    if store:
        document = write_capacity(
            BROKER_NAME,
            connection_count,
            instruments_per_connection,
            refusal_reason,
            instrument_evidence + connection_evidence,
        )
        print(f"\nstored in MongoDB stream_capacity, measured_at {document['measured_at']}")
    return 0


def main():
    """
    Parse the command line and run the capacity probe.

    Returns:
        None.

    Raises:
        SystemExit: Always, with the probe's exit status.
    """
    parser = argparse.ArgumentParser(description="Measure Zerodha's real websocket limits.")
    parser.add_argument("--ceiling", type=int, default=CONNECTION_CEILING, help="Largest number of connections to attempt.")
    parser.add_argument("--no-store", action="store_true", help="Report the measurement without recording it.")
    arguments = parser.parse_args()

    previous = read_capacity(BROKER_NAME)
    if previous is not None:
        print(f"previously measured: {previous['connection_count']} connections x {previous['instruments_per_connection']:,} instruments, at {previous['measured_at']}")
        print()

    raise SystemExit(asyncio.run(run_probe(arguments.ceiling, not arguments.no_store)))


if __name__ == "__main__":
    main()
