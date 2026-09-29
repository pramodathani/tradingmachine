"""Volume indicators: measures that combine price with traded volume.

Each method fetches the instrument's candles through `prices`, adds one or more TA-Lib columns and returns the candles. The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.on_balance_volume(days=365)
"""

import datetime

import pandas as pd
import talib

from tradingmachine.assets.analysis import price_analysis


class VolumeIndicators(price_analysis.PriceAnalysis):
    """Indicators an instrument calculates from its candles' prices and volumes."""

    def chaikin_accumulation_distribution_line(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Chaikin accumulation distribution line.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `chaikin_ad` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's accumulation distribution line for the last five days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.chaikin_accumulation_distribution_line(days=90)
            print(candles[["datetime", "close", "chaikin_ad"]].tail())
            ```

            Say whether money flowed into or out of each bank over the last month:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                candles = share.chaikin_accumulation_distribution_line(days=45)
                line = candles["chaikin_ad"]
                change = line.iloc[-1] - line.iloc[-21]
                if change > 0:
                    print(f"{symbol}: accumulation of {change:,.0f}")
                else:
                    print(f"{symbol}: distribution of {-change:,.0f}")
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
        prices["chaikin_ad"] = talib.AD(
            prices["high"],
            prices["low"],
            prices["close"],
            prices["volume"],
        )
        return prices

    def chaikin_accumulation_distribution_oscillator(
        self,
        fast_period: int = 3,
        slow_period: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Chaikin accumulation distribution oscillator.

        Args:
            fast_period: The int number of candles in the fast exponential moving average.
            slow_period: The int number of candles in the slow exponential moving average.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `chaikin_adosc<fast>_<slow>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's Chaikin oscillator for the last five days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.chaikin_accumulation_distribution_oscillator(
                days=90,
            )
            print(candles[["datetime", "close", "chaikin_adosc3_10"]].tail())
            ```

            Print the sign of a slower Chaikin oscillator for three IT shares:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                candles = share.chaikin_accumulation_distribution_oscillator(
                    fast_period=5,
                    slow_period=20,
                    days=120,
                )
                value = candles["chaikin_adosc5_20"].iloc[-1]
                if value > 0:
                    print(f"{symbol}: buying pressure {value:,.0f}")
                else:
                    print(f"{symbol}: selling pressure {value:,.0f}")
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
        prices[f"chaikin_adosc{fast_period}_{slow_period}"] = talib.ADOSC(
            prices["high"],
            prices["low"],
            prices["close"],
            prices["volume"],
            fastperiod=fast_period,
            slowperiod=slow_period,
        )
        return prices

    def on_balance_volume(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the on balance volume, measured against one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with an `obv` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's on balance volume for the last five days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.on_balance_volume(days=90)
            print(candles[["datetime", "close", "volume", "obv"]].tail())
            ```

            Check whether Reliance Industries' price and on balance volume moved the same way over the last month:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            candles = reliance.on_balance_volume(days=45)
            closes = candles["close"]
            volume_line = candles["obv"]
            price_change = closes.iloc[-1] - closes.iloc[-21]
            volume_change = volume_line.iloc[-1] - volume_line.iloc[-21]
            if (price_change > 0) == (volume_change > 0):
                print("Volume confirms the price move")
            else:
                print("Volume diverges from the price move")
            ```

            Print the on balance volume of three banks measured against their opening prices:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                candles = share.on_balance_volume(column="open", days=60)
                print(f"{symbol}: {candles['obv'].iloc[-1]:,.0f}")
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
        prices["obv"] = talib.OBV(prices[column], prices["volume"])
        return prices
