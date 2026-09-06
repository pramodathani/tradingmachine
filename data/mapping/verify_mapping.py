"""
Verification report for the mapped instrument tables.

Run it after a build, after a backfill, and after any adapter change. It only reports: nothing here raises on a finding, because the point is to see the whole picture at once rather than to stop at the first problem.

    python3 -m data.mapping.verify_mapping
    python3 -m data.mapping.verify_mapping --date 2026-09-04

Seven checks run, in the order that a problem in one would explain a problem in the next:

1. Coverage per broker, which must reconcile exactly against the raw tables.
2. Identity convergence across brokers, including a hand-checked spot list.
3. Duplicate detection, for tokens pointing at more than one instrument.
4. Index name convergence, where an alias leak shows up as two spellings of one index.
5. Resolution round-trips on a sample of stored rows.
6. Backfill sanity across dates.
7. The uncategorised profile per broker.
"""

import argparse
import datetime
import random

from sqlalchemy import create_engine, text

from data.mapping.resolution import resolve_broker_tokens, resolve_identity
from data.instruments.download_and_map import PROCESSING_ORDER
from utilities.configuration import postgres_configuration

SPOT_CHECKS = [
    ("nse", "nse_equities", "security", {"symbol": "RELIANCE"}),
    ("nse", "nse_equities", "security", {"symbol": "HDFCBANK"}),
    ("nse", "nse_equity_indices", "security", {"symbol": "NIFTY"}),
    ("nse", "nse_equity_indices", "security", {"symbol": "BANKNIFTY"}),
    ("bse", "bse_equity_indices", "security", {"symbol": "SENSEX"}),
]

ROUND_TRIP_SAMPLE_SIZE = 1000


def print_heading(title):
    """
    Print one check's heading.

    Args:
        title (str): The heading text.

    Returns:
        None
    """
    print("")
    print(f"=== {title} ===")


def check_coverage(engine, mapping_date):
    """
    Reconcile each broker's mapped rows against its raw rows for the date.

    Every raw row must end up either classified into a real segment or filed in an uncategorised bucket. A shortfall means rows were dropped somewhere, which is the failure this whole layer is meant to make impossible to hide.

    Args:
        engine: A SQLAlchemy engine for the tradingmachine database.
        mapping_date (datetime.date): The date to check.

    Returns:
        None
    """
    print_heading(f"1. coverage per broker for {mapping_date}")
    print(f"{'broker':<16} {'raw rows':>10} {'classified':>11} {'uncategorised':>14} {'share':>7}")
    with engine.connect() as connection:
        for broker in PROCESSING_ORDER:
            raw_count = connection.execute(
                text(f"SELECT count(*) AS c FROM instruments.{broker} WHERE download_date = :d"),
                {
                    "d": mapping_date,
                },
            ).one().c
            mapped = connection.execute(
                text(
                    "SELECT count(*) FILTER (WHERE m.segment NOT LIKE '%%uncategorised') AS classified, "
                    "       count(*) FILTER (WHERE m.segment LIKE '%%uncategorised') AS uncategorised "
                    "FROM instruments.broker_mappings b "
                    "JOIN instruments.master m ON m.instrument_id = b.instrument_id "
                    "WHERE b.broker = :b AND b.mapping_date = :d"
                ),
                {
                    "b": broker,
                    "d": mapping_date,
                },
            ).one()
            if raw_count == 0:
                share = 0.0
            else:
                share = 100.0 * mapped.uncategorised / raw_count
            print(
                f"{broker:<16} {raw_count:>10} {mapped.classified:>11} "
                f"{mapped.uncategorised:>14} {share:>6.2f}%"
            )
    print("")
    print("Mapped counts are distinct instruments, so they sit below the raw count wherever a")
    print("broker lists one instrument on several rows. The run summary reconciles row for row.")


def check_convergence(engine, mapping_date):
    """
    Report how many instruments are carried by several brokers, and check the spot list by hand.

    Args:
        engine: A SQLAlchemy engine for the tradingmachine database.
        mapping_date (datetime.date): The date to check.

    Returns:
        None
    """
    print_heading(f"2. identity convergence for {mapping_date}")
    with engine.connect() as connection:
        distribution = connection.execute(
            text(
                "SELECT broker_count, count(*) AS instruments FROM ("
                "  SELECT instrument_id, count(DISTINCT broker) AS broker_count "
                "  FROM instruments.broker_mappings WHERE mapping_date = :d GROUP BY 1"
                ") AS counted GROUP BY 1 ORDER BY 1"
            ),
            {
                "d": mapping_date,
            },
        ).all()
    print(f"{'brokers carrying it':>20} {'instruments':>12}")
    for row in distribution:
        print(f"{row.broker_count:>20} {row.instruments:>12}")

    print("")
    print("spot list:")
    for exchange, segment, shape, identity in SPOT_CHECKS:
        resolved_date, rows = resolve_broker_tokens(engine, exchange, segment, shape, identity, mapping_date)
        brokers = []
        for row in rows:
            brokers.append(row["broker"])
        label = identity.get("symbol")
        print(f"  {segment:<22} {str(label):<12} {len(rows)} broker(s): {', '.join(brokers) or 'none'}")


def check_duplicates(engine, mapping_date):
    """
    Report tokens that point at more than one instrument, split by how far apart those instruments are.

    A broker's token space is per exchange segment, not global, so the same number legitimately means one thing on the cash market and another on the currency derivatives market. Those cases are expected and are counted separately from the ones worth looking at.

    Args:
        engine: A SQLAlchemy engine for the tradingmachine database.
        mapping_date (datetime.date): The date to check.

    Returns:
        None
    """
    print_heading(f"3. tokens mapping to more than one instrument on {mapping_date}")
    with engine.connect() as connection:
        totals = connection.execute(
            text(
                "WITH duplicated AS ("
                "  SELECT b.broker, b.broker_token, "
                "         count(DISTINCT b.instrument_id) AS instruments, "
                "         count(DISTINCT m.exchange) AS exchanges, "
                "         count(DISTINCT m.segment) AS segments "
                "  FROM instruments.broker_mappings b "
                "  JOIN instruments.master m ON m.instrument_id = b.instrument_id "
                "  WHERE b.mapping_date = :d "
                "  GROUP BY 1, 2 HAVING count(DISTINCT b.instrument_id) > 1"
                ") "
                "SELECT count(*) AS total, "
                "       count(*) FILTER (WHERE exchanges > 1) AS across_exchanges, "
                "       count(*) FILTER (WHERE exchanges = 1 AND segments > 1) AS across_segments, "
                "       count(*) FILTER (WHERE exchanges = 1 AND segments = 1) AS within_one_segment "
                "FROM duplicated"
            ),
            {
                "d": mapping_date,
            },
        ).one()

    if totals.total == 0:
        print("no token points at more than one instrument.")
        return

    print(f"{totals.total} (broker, token) pair(s) point at more than one instrument:")
    print(f"  {totals.across_exchanges:>8} span more than one exchange       expected: token spaces are per exchange")
    print(f"  {totals.across_segments:>8} span more than one segment        expected where a row has two memberships")
    print(f"  {totals.within_one_segment:>8} sit inside one segment            worth looking at")

    if totals.within_one_segment == 0:
        return

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "WITH duplicated AS ("
                "  SELECT b.broker, b.broker_token, m.segment, "
                "         count(DISTINCT b.instrument_id) AS instruments, "
                "         count(DISTINCT m.exchange) AS exchanges, "
                "         count(DISTINCT m.segment) AS segments, "
                "         string_agg(DISTINCT coalesce(m.symbol, m.underlying_symbol), ' | ') AS names "
                "  FROM instruments.broker_mappings b "
                "  JOIN instruments.master m ON m.instrument_id = b.instrument_id "
                "  WHERE b.mapping_date = :d "
                "  GROUP BY 1, 2, 3 HAVING count(DISTINCT b.instrument_id) > 1"
                ") "
                "SELECT broker, broker_token, segment, instruments, names FROM duplicated "
                "WHERE exchanges = 1 AND segments = 1 "
                "ORDER BY instruments DESC, broker, broker_token LIMIT 20"
            ),
            {
                "d": mapping_date,
            },
        ).all()

    print("")
    print("first 20 inside one segment:")
    for row in rows:
        print(f"  {row.broker:<16} {row.broker_token:<20} {row.segment:<26} {row.instruments}: {row.names}")


def check_index_names(engine, mapping_date):
    """
    Report NSE equity index names whose normalized forms collide, which is how an alias leak shows itself.

    Args:
        engine: A SQLAlchemy engine for the tradingmachine database.
        mapping_date (datetime.date): The date to check.

    Returns:
        None
    """
    print_heading(f"4. NSE equity index name convergence for {mapping_date}")
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT upper(regexp_replace(m.symbol, '[^A-Za-z0-9]', '', 'g')) AS normalized, "
                "       count(DISTINCT m.symbol) AS spellings, "
                "       string_agg(DISTINCT m.symbol, ' | ') AS names "
                "FROM instruments.master m "
                "JOIN instruments.broker_mappings b ON b.instrument_id = m.instrument_id "
                "WHERE m.segment = 'nse_equity_indices' AND b.mapping_date = :d "
                "GROUP BY 1 HAVING count(DISTINCT m.symbol) > 1 ORDER BY 2 DESC, 1"
            ),
            {
                "d": mapping_date,
            },
        ).all()
    if not rows:
        print("no normalized index name has two spellings.")
        return
    print(f"{len(rows)} normalized name(s) carry more than one spelling:")
    for row in rows:
        print(f"  {row.normalized:<28} {row.spellings} spellings: {row.names}")


def check_round_trips(engine, mapping_date):
    """
    Resolve a random sample of stored mappings in both directions and report any mismatch.

    Args:
        engine: A SQLAlchemy engine for the tradingmachine database.
        mapping_date (datetime.date): The date to check.

    Returns:
        None
    """
    print_heading(f"5. resolution round-trips for {mapping_date}")
    with engine.connect() as connection:
        sample = connection.execute(
            text(
                "SELECT b.broker, b.broker_token, m.instrument_id, m.exchange, m.segment, m.shape, "
                "       m.symbol, m.underlying_symbol, m.expiry_date, m.strike_price, m.option_type "
                "FROM instruments.broker_mappings b "
                "JOIN instruments.master m ON m.instrument_id = b.instrument_id "
                "WHERE b.mapping_date = :d ORDER BY random() LIMIT :n"
            ),
            {
                "d": mapping_date,
                "n": ROUND_TRIP_SAMPLE_SIZE,
            },
        ).all()

    forward_failures = []
    backward_failures = []
    for row in sample:
        identity = identity_for_shape(row)
        _, tokens = resolve_broker_tokens(engine, row.exchange, row.segment, row.shape, identity, mapping_date)
        found = False
        for token_row in tokens:
            if token_row["broker"] == row.broker and token_row["broker_token"] == row.broker_token:
                found = True
        if not found:
            forward_failures.append((row.broker, row.broker_token, row.segment))

        back = resolve_identity(engine, row.broker, [row.broker_token], mapping_date)
        resolved = back.get(row.broker_token)
        if resolved is None or resolved["instrument_id"] != str(row.instrument_id):
            backward_failures.append((row.broker, row.broker_token, row.segment))

    unexplained = unexplained_backward_misses(engine, backward_failures, mapping_date)

    print(f"sampled {len(sample)} stored mapping(s).")
    print(f"identity to token:  {len(sample) - len(forward_failures)} matched, {len(forward_failures)} failed.")
    print(f"token to identity:  {len(sample) - len(backward_failures)} matched, {len(backward_failures)} answered "
          f"with a different instrument, of which {len(unexplained)} unexplained.")
    for broker, token, segment in forward_failures[:10]:
        print(f"  forward miss: {broker} {token} {segment}")
    for broker, token, segment in unexplained[:10]:
        print(f"  unexplained backward miss: {broker} {token} {segment}")
    print("")
    print("A backward answer that names a different instrument is expected on a token the broker")
    print("reuses: the look-up returns one of them by design. Such a miss on a token that is not")
    print("reused is a bug, and so is any forward miss.")


def unexplained_backward_misses(engine, backward_failures, mapping_date):
    """
    Narrow a list of backward misses down to the ones the broker's own duplicate tokens do not explain.

    Args:
        engine: A SQLAlchemy engine for the tradingmachine database.
        backward_failures (list[tuple]): The (broker, token, segment) triples that resolved to another instrument.
        mapping_date (datetime.date): The date the sample came from.

    Returns:
        list[tuple]: The subset whose token points at exactly one instrument, which means the miss has no innocent explanation.
    """
    unexplained = []
    with engine.connect() as connection:
        for broker, token, segment in backward_failures:
            count = connection.execute(
                text(
                    "SELECT count(DISTINCT instrument_id) AS instruments "
                    "FROM instruments.broker_mappings "
                    "WHERE broker = :b AND broker_token = :t AND mapping_date = :d"
                ),
                {
                    "b": broker,
                    "t": token,
                    "d": mapping_date,
                },
            ).one().instruments
            if count <= 1:
                unexplained.append((broker, token, segment))
    return unexplained


def identity_for_shape(row):
    """
    Rebuild the identity dictionary for a stored master row, using only the fields its shape defines.

    Args:
        row: One result row carrying shape, symbol, underlying_symbol, expiry_date, strike_price, and option_type.

    Returns:
        dict: The identity fields for that shape.
    """
    if row.shape == "security":
        return {
            "symbol": row.symbol,
        }
    if row.shape == "future":
        return {
            "underlying_symbol": row.underlying_symbol,
            "expiry_date": row.expiry_date,
        }
    return {
        "underlying_symbol": row.underlying_symbol,
        "expiry_date": row.expiry_date,
        "strike_price": row.strike_price,
        "option_type": row.option_type,
    }


def check_backfill(engine):
    """
    Report per-date instrument counts and the first and last seen date extremes across the whole history.

    Args:
        engine: A SQLAlchemy engine for the tradingmachine database.

    Returns:
        None
    """
    print_heading("6. backfill sanity across every mapped date")
    with engine.connect() as connection:
        per_date = connection.execute(
            text(
                "SELECT mapping_date, count(DISTINCT instrument_id) AS instruments, "
                "       count(DISTINCT broker) AS brokers "
                "FROM instruments.broker_mappings GROUP BY 1 ORDER BY 1"
            )
        ).all()
        extremes = connection.execute(
            text(
                "SELECT min(first_seen_date) AS earliest_first_seen, "
                "       max(last_seen_date) AS latest_last_seen, count(*) AS instruments "
                "FROM instruments.master"
            )
        ).one()
        inconsistent = connection.execute(
            text(
                "SELECT count(*) AS c FROM instruments.master WHERE first_seen_date > last_seen_date"
            )
        ).one().c

    print(f"{'mapping date':<14} {'instruments':>12} {'brokers':>8} {'change':>9}")
    previous = None
    for row in per_date:
        if previous is None:
            change = ""
        else:
            change = f"{row.instruments - previous:+d}"
        print(f"{str(row.mapping_date):<14} {row.instruments:>12} {row.brokers:>8} {change:>9}")
        previous = row.instruments

    print("")
    print(f"master holds {extremes.instruments} instrument(s), first seen from "
          f"{extremes.earliest_first_seen}, last seen up to {extremes.latest_last_seen}.")
    print(f"{inconsistent} instrument(s) have a first seen date after their last seen date.")


def check_uncategorised_profile(engine, mapping_date):
    """
    Report where each broker's uncategorised rows landed, so the bucket cannot quietly hide a rules gap.

    Args:
        engine: A SQLAlchemy engine for the tradingmachine database.
        mapping_date (datetime.date): The date to check.

    Returns:
        None
    """
    print_heading(f"7. uncategorised profile for {mapping_date}")
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT b.broker, m.segment, count(*) AS instruments "
                "FROM instruments.broker_mappings b "
                "JOIN instruments.master m ON m.instrument_id = b.instrument_id "
                "WHERE b.mapping_date = :d AND m.segment LIKE '%%uncategorised' "
                "GROUP BY 1, 2 ORDER BY 1, 3 DESC"
            ),
            {
                "d": mapping_date,
            },
        ).all()
    if not rows:
        print("no uncategorised rows.")
        return
    print(f"{'broker':<16} {'bucket':<22} {'instruments':>12}")
    for row in rows:
        print(f"{row.broker:<16} {row.segment:<22} {row.instruments:>12}")


def run(mapping_date):
    """
    Run every check and print the report.

    Args:
        mapping_date (datetime.date): The date the per-date checks cover.

    Returns:
        None
    """
    engine = create_engine(postgres_configuration["connection_string"])
    print(f"verification report for {mapping_date}")
    check_coverage(engine, mapping_date)
    check_convergence(engine, mapping_date)
    check_duplicates(engine, mapping_date)
    check_index_names(engine, mapping_date)
    check_round_trips(engine, mapping_date)
    check_backfill(engine)
    check_uncategorised_profile(engine, mapping_date)


def main():
    """
    Parse the command line arguments and print the verification report.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Verify the mapped instrument tables.")
    parser.add_argument("--date", help="Date to verify, as YYYY-MM-DD. Defaults to today.")
    arguments = parser.parse_args()

    if arguments.date:
        mapping_date = datetime.date.fromisoformat(arguments.date)
    else:
        mapping_date = datetime.date.today()
    run(mapping_date)


if __name__ == "__main__":
    main()
