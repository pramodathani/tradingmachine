"""Volatility indicators: measures of how far prices range.

Each method fetches the instrument's candles through `prices`, adds one or more TA-Lib columns and returns the candles. The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.average_true_range(window=14, days=365)
"""

import datetime

import pandas as pd
import talib

from tradingmachine.assets.analysis import price_analysis


class VolatilityIndicators(price_analysis.PriceAnalysis):
    """Range-based volatility indicators an instrument calculates from its candles."""

    def average_true_range(
        self,
        window: int = 14,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the average true range.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `atr_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day average true range:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.average_true_range(days=90)
            print(frame.set_index("datetime")["atr_14"].tail())
            ```

            Place a hypothetical stop two average true ranges below Vodafone Idea's close, rounded to its 0.01 tick:

            ```python
            from tradingmachine.assets import equities

            vodafone_idea = equities.Equity(exchange="nse", symbol="IDEA")
            frame = vodafone_idea.average_true_range(window=14, days=90)
            close = frame["close"].iloc[-1]
            average_true_range = frame["atr_14"].iloc[-1]
            stop_level = round(close - 2 * average_true_range, 2)
            print(f"Close {close}, ATR {average_true_range:.2f}")
            print(f"Stop level {stop_level}")
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
        prices[f"atr_{window}"] = talib.ATR(
            prices["high"],
            prices["low"],
            prices["close"],
            timeperiod=window,
        )
        return prices

    def normalized_average_true_range(
        self,
        window: int = 14,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the average true range as a percentage of the close.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `natr<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day average true range as a percentage of the close:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.normalized_average_true_range(days=90)
            print(frame.set_index("datetime")["natr14"].tail())
            ```

            Rank four shares from the most to the least volatile by their latest value:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
                "RELIANCE",
            ]
            latest_values = {}
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                frame = share.normalized_average_true_range(window=14, days=90)
                latest_values[symbol] = frame["natr14"].iloc[-1]
            ranked = sorted(latest_values, key=latest_values.get, reverse=True)
            for symbol in ranked:
                print(f"{symbol}: {latest_values[symbol]:.2f}%")
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
        prices[f"natr{window}"] = talib.NATR(
            prices["high"],
            prices["low"],
            prices["close"],
            timeperiod=window,
        )
        return prices

    def true_range(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds each candle's true range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `tr` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's true range:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.true_range(days=30)
            print(frame.set_index("datetime")["tr"].tail())
            ```

            Find the day with NIFTY's widest true range in the last half year:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.true_range(days=180)
            widest_row = frame["tr"].idxmax()
            widest_day = frame.loc[widest_row, "datetime"].date()
            print(f"{widest_day}: {frame.loc[widest_row, 'tr']:.2f} points")
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
        prices["tr"] = talib.TRANGE(prices["high"], prices["low"], prices["close"])
        return prices
