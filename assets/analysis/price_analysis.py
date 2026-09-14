"""The shared base of every candle analysis class in `assets.analysis`.

Each analysis class inherits `PriceAnalysis` and calls `prices` to fetch candles. `assets.instruments.Instrument` inherits every analysis class and supplies the real `prices`, which reads UBI.

Typical usage example:

  class OverlapStudies(price_analysis.PriceAnalysis):
      def simple_moving_average(self, window=10):
          prices = self.prices(days=365)
"""

import datetime

import pandas as pd


class PriceAnalysis:
    """A source of candles that analysis methods can be written against."""

    def prices(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Fetches candles for a range, which a subclass must provide.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of candles with `exchange`, `segment`, `interval`, `datetime`, `open`, `high`, `low`, `close`, `volume` and `oi` columns, or None when there are no candles.

        Raises:
            NotImplementedError: Always, because only a subclass knows where candles come from.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must define prices to use PriceAnalysis"
        )
