"""
Command line entry point for the daily instrument job: download every broker's master, then map them all into the unified tables.

Run without arguments to do both stages for today. One broker failing at either stage is reported and does not stop the others, because a single broker's file being late or malformed should not cost the day's whole snapshot.

    python3 -m data.instruments.download_and_map
    python3 -m data.instruments.download_and_map --broker zerodha
    python3 -m data.instruments.download_and_map --date 2026-09-04
    python3 -m data.instruments.download_and_map --bootstrap
    python3 -m data.instruments.download_and_map --broker indmoney --indmoney-access-token TOKEN

Either stage can be run alone, because the two are not equally repeatable. A download can only ever fetch today's file, since the brokers publish no history, while the mapping can be re-run over any date already stored. So a mapping fix is applied by re-running the mapping over stored dates, never by downloading again.

    python3 -m data.instruments.download_and_map --skip-mapping
    python3 -m data.instruments.download_and_map --mapping-only --date 2026-09-04
    python3 -m data.instruments.download_and_map --backfill

The mapping runs after every download rather than after each one, and its broker order is fixed rather than alphabetical. Both follow from the same thing: the cross-broker classification aids pool the whole day's raw files, and several adapters resolve their index names against the index rows already written for the same date, so the brokers publishing a clean index vocabulary have to go first.
"""

import argparse
import datetime
import traceback

from sqlalchemy import create_engine, text

from data.instruments.zerodha import ZerodhaInstruments
from data.instruments.dhan import DhanInstruments
from data.instruments.groww import GrowwInstruments
from data.instruments.stoxkart import StoxkartInstruments
from data.instruments.flattrade import FlattradeInstruments
from data.instruments.fyers import FyersInstruments
from data.instruments.kotak import KotakInstruments
from data.instruments.shoonya import ShoonyaInstruments
from data.instruments.wisdom_capital import WisdomCapitalInstruments
from data.instruments.indmoney import IndMoneyInstruments
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

BROKER_CLASSES = {
    "zerodha": ZerodhaInstruments,
    "dhan": DhanInstruments,
    "groww": GrowwInstruments,
    "stoxkart": StoxkartInstruments,
    "flattrade": FlattradeInstruments,
    "fyers": FyersInstruments,
    "kotak": KotakInstruments,
    "shoonya": ShoonyaInstruments,
    "wisdom_capital": WisdomCapitalInstruments,
    "indmoney": IndMoneyInstruments,
}

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


def download_one(broker_name, download_date, bootstrap, indmoney_access_token=None):
    """
    Download and store one broker's instrument master, then check its row count.

    Args:
        broker_name (str): Key into BROKER_CLASSES.
        download_date (datetime.date): Snapshot date to record.
        bootstrap (bool): When True, replace that date's stored rows rather than skipping.
        indmoney_access_token (str | None): Token for IND Money, the one broker needing authentication. Ignored for every other broker.

    Returns:
        dict: Keys 'broker', 'rows' and 'error', where 'error' is None on success.
    """
    print(f"--- {broker_name} ---")
    if broker_name == "indmoney":
        ingester = IndMoneyInstruments(access_token=indmoney_access_token)
    else:
        ingester = BROKER_CLASSES[broker_name]()
    try:
        rows = ingester.ingest(download_date=download_date, bootstrap=bootstrap)
        ingester.check_row_count_deviation(download_date)
        return {"broker": broker_name, "rows": rows, "error": None}
    except Exception as error:
        print(f"{broker_name}: FAILED with {type(error).__name__}: {error}")
        traceback.print_exc()
        return {"broker": broker_name, "rows": 0, "error": f"{type(error).__name__}: {error}"}


def download_all(download_date, broker_name=None, bootstrap=False, indmoney_access_token=None):
    """
    Download and store the instrument masters for one broker or for all of them.

    Args:
        download_date (datetime.date): Snapshot date to record.
        broker_name (str | None): A single broker to run. None runs every broker.
        bootstrap (bool): When True, replace that date's stored rows rather than skipping.
        indmoney_access_token (str | None): Token for IND Money. When omitted, the token configured in the environment is used.

    Returns:
        list[dict]: One result dictionary per broker attempted.
    """
    print(f"=== downloading for {download_date} ===")
    broker_names = [broker_name] if broker_name else list(BROKER_CLASSES)

    results = []
    for name in broker_names:
        results.append(download_one(name, download_date, bootstrap, indmoney_access_token))

    print("")
    print(f"=== download summary for {download_date} ===")
    for result in results:
        status = result["error"] if result["error"] else f"{result['rows']} row(s)"
        print(f"{result['broker']:<16} {status}")
    failed = []
    for result in results:
        if result["error"]:
            failed.append(result["broker"])
    if failed:
        print(f"{len(failed)} broker(s) failed to download: {', '.join(failed)}")
    return results


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
    Map one broker's stored raw rows for one date into the unified tables.

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


def map_all(engine, mapping_date, broker_name=None):
    """
    Map one date, for one broker or for every broker in the fixed processing order.

    A broker with no raw rows stored for the date is skipped with a printed notice, so a late or failed download degrades to being absent from that day's mapping rather than aborting it.

    Args:
        engine: A SQLAlchemy engine for the black_box database.
        mapping_date (datetime.date): The snapshot date to map.
        broker_name (str | None): A single broker to run. None runs every broker.

    Returns:
        list[dict]: One result dictionary per broker attempted.
    """
    print("")
    print(f"=== mapping for {mapping_date} ===")
    if broker_name:
        broker_names = [broker_name]
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
        print(f"{len(failed)} broker(s) failed to map: {', '.join(failed)}")
    return results


def run(broker_name=None, download_date=None, bootstrap=False, indmoney_access_token=None,
        skip_mapping=False, mapping_only=False, backfill=False):
    """
    Run the daily instrument job: download the brokers' masters, then map them into the unified tables.

    Args:
        broker_name (str | None): A single broker to run. None runs every broker.
        download_date (datetime.date | None): Snapshot date to record and map. Defaults to today.
        bootstrap (bool): When True, replace that date's stored rows rather than skipping.
        indmoney_access_token (str | None): Token for IND Money. When omitted, the token configured in the environment is used.
        skip_mapping (bool): When True, download without mapping.
        mapping_only (bool): When True, map what is already stored without downloading.
        backfill (bool): When True, map every stored snapshot date oldest first and do not download at all, so that first and last seen dates come out right.

    Returns:
        dict: Keys "downloads" and "mappings", each a list of per-broker result dictionaries.
    """
    engine = create_engine(postgres_configuration["connection_string"])
    download_results = []
    mapping_results = []

    if backfill:
        dates = stored_download_dates(engine)
        if not dates:
            print("no stored dates to backfill.")
            return {
                "downloads": download_results,
                "mappings": mapping_results,
            }
        print(f"backfilling {len(dates)} stored date(s), from {dates[0]} to {dates[-1]}.")
        for one_date in dates:
            mapping_results.extend(map_all(engine, one_date, broker_name))
        return {
            "downloads": download_results,
            "mappings": mapping_results,
        }

    job_date = download_date or datetime.date.today()
    if not mapping_only:
        download_results = download_all(job_date, broker_name, bootstrap, indmoney_access_token)
    if not skip_mapping:
        mapping_results = map_all(engine, job_date, broker_name)

    return {
        "downloads": download_results,
        "mappings": mapping_results,
    }


def main():
    """
    Parse the command line arguments and run the daily instrument job.

    Returns:
        dict: The result dictionary described in run.
    """
    parser = argparse.ArgumentParser(
        description="Download the brokers' daily instrument masters and map them into the unified tables."
    )
    parser.add_argument("--broker", choices=sorted(BROKER_CLASSES), help="Run a single broker instead of all of them.")
    parser.add_argument("--date", help="Snapshot date to record and map, as YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--bootstrap", action="store_true", help="Replace this date's stored rows rather than skipping.")
    parser.add_argument("--indmoney-access-token", help="Access token for IND Money. Overrides BLACK_BOX_INDMONEY_ACCESS_TOKEN.")
    parser.add_argument("--skip-mapping", action="store_true", help="Download without mapping.")
    parser.add_argument("--mapping-only", action="store_true", help="Map what is already stored without downloading.")
    parser.add_argument("--backfill", action="store_true", help="Map every stored snapshot date, oldest first, without downloading.")
    arguments = parser.parse_args()

    download_date = datetime.date.fromisoformat(arguments.date) if arguments.date else None
    return run(
        broker_name=arguments.broker,
        download_date=download_date,
        bootstrap=arguments.bootstrap,
        indmoney_access_token=arguments.indmoney_access_token,
        skip_mapping=arguments.skip_mapping,
        mapping_only=arguments.mapping_only,
        backfill=arguments.backfill,
    )


if __name__ == "__main__":
    main()
