"""UBI's answer to `GET /api/instruments/prices`, kept whole.

UBI answers with the candles as rows under `columns`, together with facts about them: which price basis they are on, whether the instrument can be adjusted at all, whether they came from UBI's cache or its database, and the range they cover. `PricesDocument` keeps the answer exactly as it came and offers both the facts and the candles as a pandas DataFrame.

Typical usage example:

  document = catalogue.prices_document(instrument_id, days=365)
  print(document.price_basis, document.source)
  frame = document.frame("nse", "nse_equities", "day")
"""

import zoneinfo

import pandas as pd

INDIA_TIME_ZONE = zoneinfo.ZoneInfo("Asia/Kolkata")


class PricesDocument:
    """One answer from UBI's prices route.

    Attributes:
        document: The dict exactly as UBI answered, for callers that pass it on unchanged.
        columns: A list of the str names of each candle row's cells, such as `time`, `open` and `close`.
        candles: A list of candle rows, each a list of cells in the order of columns, oldest first.
        interval: The str candle interval UBI served, such as `day`, or None when the answer does not say.
        price_basis: The str basis of the prices, `adjusted`, `unadjusted` or `as_served`, or None.
        adjustable: The bool UBI reports for whether the instrument's prices can be adjusted for corporate actions, or None.
        source: The str place UBI read the candles from, `cache` or `database`, or None.
        from_date: The str first day of the range UBI read, as `YYYY-MM-DD`, or None.
        to_date: The str last day of the range UBI read, as `YYYY-MM-DD`, or None.
    """

    def __init__(self, document: dict):
        """Initialises the document from UBI's answer.

        Args:
            document: The dict UBI returned from `/api/instruments/prices`.

        Raises:
            Nothing.
        """
        self.document = document
        self.columns = list(document.get("columns") or [])
        self.candles = list(document.get("candles") or [])
        self.interval = document.get("interval")
        self.price_basis = document.get("price_basis")
        self.adjustable = document.get("adjustable")
        self.source = document.get("source")
        self.from_date = document.get("from")
        self.to_date = document.get("to")

    @property
    def is_empty(self) -> bool:
        """A bool that is True when UBI has no candles for the range."""
        return not self.candles

    def frame(self, exchange: str, segment: str, interval: str) -> pd.DataFrame | None:
        """Turns the candles into a DataFrame labelled with the instrument and interval.

        Args:
            exchange: The str exchange to put in the `exchange` column, such as `nse`.
            segment: The str segment to put in the `segment` column, such as `nse_equities`.
            interval: The str interval to put in the `interval` column, such as `day`.

        Returns:
            A pandas.DataFrame sorted by time, with `exchange`, `segment`, `interval`, `datetime` in India time, and one column per remaining name in columns, such as `open`, `high`, `low`, `close`, `volume`, `oi` and, for adjusted prices, `price_factor`; or None when there are no candles.

        Raises:
            Nothing.
        """
        if self.is_empty:
            return None
        frame = pd.DataFrame(self.candles, columns=self.columns)
        frame = frame.rename(columns={"time": "datetime"})
        frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.tz_convert(
            INDIA_TIME_ZONE
        )
        frame.insert(0, "interval", interval)
        frame.insert(0, "segment", segment)
        frame.insert(0, "exchange", exchange)
        return frame.sort_values("datetime").reset_index(drop=True)
