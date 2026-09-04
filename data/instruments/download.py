"""
Command line entry point for downloading the brokers' daily instrument masters.

Run without arguments to fetch every broker. One broker failing is reported and does not stop the others, because a single broker's file being late or malformed should not cost the day's whole snapshot.

    python3 -m data.instruments.download
    python3 -m data.instruments.download --broker zerodha
    python3 -m data.instruments.download --date 2026-09-04
    python3 -m data.instruments.download --bootstrap
"""

import argparse
import datetime
import traceback

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


def download_one(broker_name, download_date, bootstrap):
    """
    Download and store one broker's instrument master, then check its row count.

    Args:
        broker_name (str): Key into BROKER_CLASSES.
        download_date (datetime.date): Snapshot date to record.
        bootstrap (bool): When True, ingest even though that date is already present.

    Returns:
        dict: Keys 'broker', 'rows' and 'error', where 'error' is None on success.
    """
    print(f"--- {broker_name} ---")
    ingester = BROKER_CLASSES[broker_name]()
    try:
        rows = ingester.ingest(download_date=download_date, bootstrap=bootstrap)
        ingester.check_row_count_deviation(download_date)
        return {"broker": broker_name, "rows": rows, "error": None}
    except Exception as error:
        print(f"{broker_name}: FAILED with {type(error).__name__}: {error}")
        traceback.print_exc()
        return {"broker": broker_name, "rows": 0, "error": f"{type(error).__name__}: {error}"}


def run(broker_name=None, download_date=None, bootstrap=False):
    """
    Download and store the instrument masters for one broker or for all of them.

    Args:
        broker_name (str | None): A single broker to run. None runs every broker.
        download_date (datetime.date | None): Snapshot date to record. Defaults to today.
        bootstrap (bool): When True, ingest even though that date is already present.

    Returns:
        list[dict]: One result dictionary per broker attempted.
    """
    download_date = download_date or datetime.date.today()
    broker_names = [broker_name] if broker_name else list(BROKER_CLASSES)

    results = []
    for name in broker_names:
        results.append(download_one(name, download_date, bootstrap))

    print("")
    print(f"=== summary for {download_date} ===")
    for result in results:
        status = result["error"] if result["error"] else f"{result['rows']} row(s)"
        print(f"{result['broker']:<16} {status}")
    failed = [result["broker"] for result in results if result["error"]]
    if failed:
        print(f"{len(failed)} broker(s) failed: {', '.join(failed)}")
    return results


def main():
    """
    Parse the command line arguments and run the download.

    Returns:
        list[dict]: One result dictionary per broker attempted.
    """
    parser = argparse.ArgumentParser(description="Download the brokers' daily instrument masters into TimescaleDB.")
    parser.add_argument("--broker", choices=sorted(BROKER_CLASSES), help="Run a single broker instead of all of them.")
    parser.add_argument("--date", help="Snapshot date to record, as YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--bootstrap", action="store_true", help="Ingest even though this date is already stored.")
    arguments = parser.parse_args()

    download_date = datetime.date.fromisoformat(arguments.date) if arguments.date else None
    return run(broker_name=arguments.broker, download_date=download_date, bootstrap=arguments.bootstrap)


if __name__ == "__main__":
    main()
