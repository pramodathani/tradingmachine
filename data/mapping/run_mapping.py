"""
Command line entry point for mapping the stored instrument masters into the unified tables.

Run without arguments to map every broker for today. One broker failing is reported and does not stop the others, for the same reason the download works that way: one broker's file being late or malformed should not cost the day's whole mapping.

    python3 -m data.mapping.run_mapping
    python3 -m data.mapping.run_mapping --broker zerodha
    python3 -m data.mapping.run_mapping --date 2026-09-04
    python3 -m data.mapping.run_mapping --backfill

The broker order is fixed and matters. Several adapters resolve their index names against the index rows already written for the same date, so the brokers that publish a clean index vocabulary run before the brokers that need normalizing against it. The cross-broker classification aids read the raw tables directly and so do not depend on the order, but they do depend on the whole day's download being present, which is why the mapping runs after every download rather than after each one.
"""

import argparse
import datetime
import traceback

from sqlalchemy import create_engine, text

from data.mapping.dhan import DhanMappingAdapter
from data.mapping.kotak import KotakMappingAdapter
from data.mapping.groww import GrowwMappingAdapter
from data.mapping.stoxkart import StoxkartMappingAdapter
from data.mapping.fyers import FyersMappingAdapter
from data.mapping.wisdom_capital import WisdomCapitalMappingAdapter
from data.mapping.indmoney import IndMoneyMappingAdapter
from data.mapping.flattrade import FlattradeMappingAdapter
from data.mapping.shoonya import ShoonyaMappingAdapter
from data.mapping.zerodha import ZerodhaMappingAdapter
from utilities.configuration import postgres_configuration

ADAPTER_CLASSES = {
    "dhan": DhanMappingAdapter,
    "kotak": KotakMappingAdapter,
    "groww": GrowwMappingAdapter,
    "stoxkart": StoxkartMappingAdapter,
    "fyers": FyersMappingAdapter,
    "wisdom_capital": WisdomCapitalMappingAdapter,
    "indmoney": IndMoneyMappingAdapter,
    "flattrade": FlattradeMappingAdapter,
    "shoonya": ShoonyaMappingAdapter,
    "zerodha": ZerodhaMappingAdapter,
}

PROCESSING_ORDER = [
    "dhan",
    "kotak",
    "groww",
    "stoxkart",
    "fyers",
    "wisdom_capital",
    "indmoney",
    "flattrade",
    "shoonya",
    "zerodha",
]


def has_raw_rows(engine, broker, mapping_date):
    """
    Check whether a broker's raw table holds any rows for a date.

    Args:
        engine: A SQLAlchemy engine for the black_box database.
        broker (str): The broker name, which is also its raw table name.
        mapping_date (datetime.date): The snapshot date to check.

    Returns:
        bool: True when at least one raw row exists for that date.
    """
    with engine.connect() as connection:
        count = connection.execute(
            text(f"SELECT count(*) AS row_count FROM instruments.{broker} WHERE download_date = :d"),
            {
                "d": mapping_date,
            },
        ).one()
    return count.row_count > 0


def stored_download_dates(engine):
    """
    List every date any broker has stored raw rows for, oldest first.

    Args:
        engine: A SQLAlchemy engine for the black_box database.

    Returns:
        list[datetime.date]: The distinct snapshot dates, ascending.
    """
    queries = []
    for broker in PROCESSING_ORDER:
        queries.append(f"SELECT DISTINCT download_date FROM instruments.{broker}")
    union = " UNION ".join(queries)

    with engine.connect() as connection:
        result = connection.execute(text(f"SELECT download_date FROM ({union}) AS d ORDER BY download_date")).all()

    dates = []
    for row in result:
        dates.append(row.download_date)
    return dates


def map_one(broker, mapping_date):
    """
    Map one broker's raw rows for one date.

    Args:
        broker (str): Key into ADAPTER_CLASSES.
        mapping_date (datetime.date): The snapshot date to map.

    Returns:
        dict: Keys "broker", "matched", "uncategorised", "instruments", and "error", where "error" is None on success.
    """
    print(f"--- {broker} ---")
    try:
        summary = ADAPTER_CLASSES[broker]().run(mapping_date)
        return {
            "broker": broker,
            "matched": summary["matched"],
            "uncategorised": summary["uncategorised"],
            "instruments": summary["instruments_upserted"],
            "error": None,
        }
    except Exception as error:
        print(f"{broker}: FAILED with {type(error).__name__}: {error}")
        traceback.print_exc()
        return {
            "broker": broker,
            "matched": 0,
            "uncategorised": 0,
            "instruments": 0,
            "error": f"{type(error).__name__}: {error}",
        }


def run_one_date(engine, mapping_date, broker=None):
    """
    Map one date, for one broker or for every broker in the fixed order.

    Args:
        engine: A SQLAlchemy engine for the black_box database.
        mapping_date (datetime.date): The snapshot date to map.
        broker (str | None): A single broker to run. None runs every broker.

    Returns:
        list[dict]: One result dictionary per broker attempted.
    """
    if broker:
        broker_names = [broker]
    else:
        broker_names = list(PROCESSING_ORDER)

    results = []
    for name in broker_names:
        if not has_raw_rows(engine, name, mapping_date):
            print(f"{name}: no raw rows stored for {mapping_date}, skipping.")
            continue
        results.append(map_one(name, mapping_date))

    print("")
    print(f"=== mapping summary for {mapping_date} ===")
    for result in results:
        if result["error"]:
            status = result["error"]
        else:
            status = (
                f"{result['matched']} classified, {result['uncategorised']} uncategorised, "
                f"{result['instruments']} instrument(s)"
            )
        print(f"{result['broker']:<16} {status}")
    failed = []
    for result in results:
        if result["error"]:
            failed.append(result["broker"])
    if failed:
        print(f"{len(failed)} broker(s) failed: {', '.join(failed)}")
    return results


def run(broker=None, mapping_date=None, backfill=False):
    """
    Map one date, or every stored date when backfilling.

    Args:
        broker (str | None): A single broker to run. None runs every broker.
        mapping_date (datetime.date | None): The snapshot date to map. Defaults to today.
        backfill (bool): When True, map every stored snapshot date oldest first, so first and last seen dates come out right.

    Returns:
        list[dict]: One result dictionary per broker per date attempted.
    """
    engine = create_engine(postgres_configuration["connection_string"])

    if backfill:
        dates = stored_download_dates(engine)
        print(f"backfilling {len(dates)} stored date(s), from {dates[0]} to {dates[-1]}." if dates else "no stored dates to backfill.")
    else:
        dates = [mapping_date or datetime.date.today()]

    results = []
    for one_date in dates:
        results.extend(run_one_date(engine, one_date, broker))
    return results


def main():
    """
    Parse the command line arguments and run the mapping.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Map the brokers' stored instrument masters into the unified tables.")
    parser.add_argument("--broker", choices=sorted(ADAPTER_CLASSES), help="Run a single broker instead of all of them.")
    parser.add_argument("--date", help="Snapshot date to map, as YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--backfill", action="store_true", help="Map every stored snapshot date, oldest first.")
    arguments = parser.parse_args()

    mapping_date = None
    if arguments.date:
        mapping_date = datetime.date.fromisoformat(arguments.date)

    run(broker=arguments.broker, mapping_date=mapping_date, backfill=arguments.backfill)


if __name__ == "__main__":
    main()
