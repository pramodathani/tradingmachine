"""Price transforms: single prices that summarise each candle.

Each method fetches the instrument's candles through `prices`, adds one or more TA-Lib columns and returns the candles. The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.typical_price(days=30)
"""

import datetime

import pandas as pd
import talib

from tradingmachine.assets.analysis import price_analysis


class PriceTransforms(price_analysis.PriceAnalysis):
    """Per-candle price summaries an instrument calculates from its candles."""

    def average_price(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the average of each candle's open, high, low and close.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with an `avg_price` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's average of open, high, low and close:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.average_price(days=30)
            print(frame.set_index("datetime")["avg_price"].tail())
            ```

            Count the days in the last quarter on which NIFTY closed above its average price:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.average_price(days=90)
            above = (frame["close"] > frame["avg_price"]).sum()
            total = len(frame)
            print(f"Closed above its average price on {above} of {total} days")
            ```
        """
        prices = self.prices(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if prices is None:
            return None
        prices["avg_price"] = talib.AVGPRICE(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def median_price(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the midpoint of each candle's high and low.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `med_price` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's midpoint of high and low:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.median_price(days=30)
            print(frame.set_index("datetime")["med_price"].tail())
            ```

            Print NIFTY's median price for every day of a fixed week:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.median_price(
                from_date="2026-09-21",
                to_date="2026-09-25",
            )
            print(frame.set_index("datetime")["med_price"])
            ```
        """
        prices = self.prices(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if prices is None:
            return None
        prices["med_price"] = talib.MEDPRICE(prices["high"], prices["low"])
        return prices

    def typical_price(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the average of each candle's high, low and close.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `typ_price` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's typical price:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.typical_price(days=30)
            print(frame.set_index("datetime")["typ_price"].tail())
            ```

            Work out Infosys's volume-weighted typical price over the last month:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.typical_price(days=30)
            traded_value = (frame["typ_price"] * frame["volume"]).sum()
            weighted_price = traded_value / frame["volume"].sum()
            print(f"Volume-weighted typical price: {weighted_price:.2f}")
            ```
        """
        prices = self.prices(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if prices is None:
            return None
        prices["typ_price"] = talib.TYPPRICE(
            prices["high"], prices["low"], prices["close"]
        )
        return prices

    def weighted_close(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds each candle's weighted close, which counts the close twice alongside the high and low.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `wght_close` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's weighted close:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.weighted_close(days=30)
            print(frame.set_index("datetime")["wght_close"].tail())
            ```

            Compare NIFTY's latest weighted close with its latest typical price:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            weighted_frame = nifty.weighted_close(days=30)
            typical_frame = nifty.typical_price(days=30)
            print(f"Weighted close {weighted_frame['wght_close'].iloc[-1]:.2f}")
            print(f"Typical price {typical_frame['typ_price'].iloc[-1]:.2f}")
            ```
        """
        prices = self.prices(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if prices is None:
            return None
        prices["wght_close"] = talib.WCLPRICE(
            prices["high"], prices["low"], prices["close"]
        )
        return prices
