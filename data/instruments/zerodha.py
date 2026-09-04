"""
Zerodha instrument master ingestion.

Zerodha publishes one public CSV covering every exchange it supports.
"""

import pandas

from data.instruments.base import BrokerInstruments

INSTRUMENTS_URL = "https://api.kite.trade/instruments"


class ZerodhaInstruments(BrokerInstruments):
    """
    Downloads Zerodha's daily instrument master.

    Attributes:
        BROKER_NAME (str): Always "zerodha".
        DEDUPE_KEY_COLUMNS (list[str]): The instrument token, which Zerodha makes unique across every exchange.
        DEDUPE_SORT_COLUMN (str | None): Unused, the key alone is unambiguous.
    """

    BROKER_NAME = "zerodha"
    DEDUPE_KEY_COLUMNS = [
        "instrument_token",
    ]
    DEDUPE_SORT_COLUMN = None

    def download(self):
        """
        Fetch Zerodha's single instrument master CSV.

        Returns:
            pandas.DataFrame: Every row Zerodha published, read as text.
        """
        return pandas.read_csv(INSTRUMENTS_URL, dtype=str)
