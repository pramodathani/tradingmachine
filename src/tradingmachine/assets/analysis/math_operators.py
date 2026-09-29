"""Math operators: arithmetic between candle columns and rolling extremes of one column.

Each method fetches the instrument's candles through `prices`, adds one or more TA-Lib columns and returns the candles. The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.subtract(first_column="high", second_column="low", days=30)
"""

import datetime

import pandas as pd
import talib

from tradingmachine.assets.analysis import price_analysis


class MathOperators(price_analysis.PriceAnalysis):
    """Arithmetic and rolling extremes an instrument calculates from its candle columns."""

    def add(
        self,
        first_column: str = "high",
        second_column: str = "low",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the sum of two candle columns.

        Args:
            first_column: The str name of the first candle column.
            second_column: The str name of the second candle column.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `sum` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Add Infosys's high and low and halve the sum to get each day's midpoint:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.add(days=30)
            midpoint = frame["sum"] / 2
            print(midpoint.tail())
            ```

            Add NIFTY's open and close:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.add(
                first_column="open",
                second_column="close",
                days=30,
            )
            print(frame.set_index("datetime")["sum"].tail())
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
        prices["sum"] = talib.ADD(prices[first_column], prices[second_column])
        return prices

    def subtract(
        self,
        first_column: str = "high",
        second_column: str = "low",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the second candle column subtracted from the first.

        Args:
            first_column: The str name of the first candle column.
            second_column: The str name of the second candle column.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `difference` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five of Infosys's daily ranges, the high minus the low:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.subtract(days=30)
            print(frame.set_index("datetime")["difference"].tail())
            ```

            Count NIFTY's up days by subtracting the open from the close:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.subtract(
                first_column="close",
                second_column="open",
                days=90,
            )
            up_days = (frame["difference"] > 0).sum()
            print(f"Closed above its open on {up_days} of {len(frame)} days")
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
        prices["difference"] = talib.SUB(prices[first_column], prices[second_column])
        return prices

    def multiply(
        self,
        first_column: str = "high",
        second_column: str = "low",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the product of two candle columns.

        Args:
            first_column: The str name of the first candle column.
            second_column: The str name of the second candle column.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `product` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five products of Infosys's high and low:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.multiply(days=30)
            print(frame.set_index("datetime")["product"].tail())
            ```

            Work out the rupee value Infosys traded each day as the close times the volume:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.multiply(
                first_column="close",
                second_column="volume",
                days=30,
            )
            crores = frame.set_index("datetime")["product"] / 10000000
            print(crores.round(1).tail())
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
        prices["product"] = talib.MULT(prices[first_column], prices[second_column])
        return prices

    def divide(
        self,
        first_column: str = "high",
        second_column: str = "low",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the first candle column divided by the second.

        Args:
            first_column: The str name of the first candle column.
            second_column: The str name of the second candle column.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `quotient` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's daily range as a percentage of the low, from the high divided by the low:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.divide(days=30)
            range_percent = (frame["quotient"] - 1) * 100
            print(range_percent.round(2).tail())
            ```

            Print NIFTY's close divided by its open for the last five days:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.divide(
                first_column="close",
                second_column="open",
                days=30,
            )
            print(frame.set_index("datetime")["quotient"].tail())
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
        prices["quotient"] = talib.DIV(prices[first_column], prices[second_column])
        return prices

    def maximum(
        self,
        column: str = "close",
        window: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the highest value of one candle column over each window.

        Args:
            column: The str name of the candle column to use, such as `close`.
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `max` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five of Infosys's highest closes over 20 days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.maximum(window=20, days=90)
            print(frame.set_index("datetime")["max"].tail())
            ```

            Count the days on which NIFTY's high set a new 50-day high:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.maximum(column="high", window=50, days=365)
            new_highs = (frame["high"] == frame["max"]).sum()
            print(f"New 50-day highs on {new_highs} days")
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
        prices["max"] = talib.MAX(prices[column], timeperiod=window)
        return prices

    def minimum(
        self,
        column: str = "close",
        window: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the lowest value of one candle column over each window.

        Args:
            column: The str name of the candle column to use, such as `close`.
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `min` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five of Infosys's lowest closes over 20 days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.minimum(window=20, days=90)
            print(frame.set_index("datetime")["min"].tail())
            ```

            Count the days on which NIFTY's low set a new 50-day low:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.minimum(column="low", window=50, days=365)
            new_lows = (frame["low"] == frame["min"]).sum()
            print(f"New 50-day lows on {new_lows} days")
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
        prices["min"] = talib.MIN(prices[column], timeperiod=window)
        return prices

    def maximum_index(
        self,
        column: str = "close",
        window: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the row position of the highest value of one candle column over each window.

        Args:
            column: The str name of the candle column to use, such as `close`.
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `maxindex` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the row positions of Infosys's highest close in each 20-day window:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.maximum_index(window=20, days=90)
            print(frame.set_index("datetime")["maxindex"].tail())
            ```

            Print the date of NIFTY's highest close in the last 20 days:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.maximum_index(window=20, days=90)
            position = int(frame["maxindex"].iloc[-1])
            highest_day = frame.loc[position, "datetime"].date()
            print(highest_day, frame.loc[position, "close"])
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
        prices["maxindex"] = talib.MAXINDEX(prices[column], timeperiod=window)
        return prices

    def minimum_index(
        self,
        column: str = "close",
        window: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the row position of the lowest value of one candle column over each window.

        Args:
            column: The str name of the candle column to use, such as `close`.
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `minindex` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the row positions of Infosys's lowest close in each 20-day window:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.minimum_index(window=20, days=90)
            print(frame.set_index("datetime")["minindex"].tail())
            ```

            Print how many days ago NIFTY made its lowest close of the last 20 days:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.minimum_index(window=20, days=90)
            position = int(frame["minindex"].iloc[-1])
            print(f"{len(frame) - 1 - position} trading days ago")
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
        prices["minindex"] = talib.MININDEX(prices[column], timeperiod=window)
        return prices

    def minimum_maximum(
        self,
        column: str = "close",
        window: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the lowest and highest values of one candle column over each window.

        Args:
            column: The str name of the candle column to use, such as `close`.
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `min` and `max` columns added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five days of Infosys's 20-day lowest and highest close:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.minimum_maximum(window=20, days=90)
            columns = [
                "datetime",
                "min",
                "max",
            ]
            print(frame[columns].tail())
            ```

            Print where NIFTY's latest close sits within its 20-day range, as a percentage:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.minimum_maximum(window=20, days=90)
            latest = frame.iloc[-1]
            distance_from_low = latest["close"] - latest["min"]
            width = latest["max"] - latest["min"]
            position = distance_from_low / width
            print(f"{position:.0%} of the way from the low to the high")
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
        first, second = talib.MINMAX(prices[column], timeperiod=window)
        prices["min"] = first
        prices["max"] = second
        return prices

    def minimum_maximum_index(
        self,
        column: str = "close",
        window: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the row positions of the lowest and highest values of one candle column over each window.

        Args:
            column: The str name of the candle column to use, such as `close`.
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `minindex` and `maxindex` columns added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five days of Infosys's 20-day lowest and highest row positions:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.minimum_maximum_index(window=20, days=90)
            columns = [
                "datetime",
                "minindex",
                "maxindex",
            ]
            print(frame[columns].tail())
            ```

            Say whether NIFTY's 20-day low or high came more recently:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.minimum_maximum_index(window=20, days=90)
            low_position = int(frame["minindex"].iloc[-1])
            high_position = int(frame["maxindex"].iloc[-1])
            if high_position > low_position:
                print("The high came after the low, so the swing is upward")
            else:
                print("The low came after the high, so the swing is downward")
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
        first, second = talib.MINMAXINDEX(prices[column], timeperiod=window)
        prices["minindex"] = first
        prices["maxindex"] = second
        return prices
