"""Math transforms: element-by-element mathematical functions of one candle column.

Each method fetches the instrument's candles through `prices`, adds one or more TA-Lib columns and returns the candles. The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.natural_logarithm(days=365)
"""

import datetime

import pandas as pd
import talib

from tradingmachine.assets.analysis import price_analysis


class MathTransforms(price_analysis.PriceAnalysis):
    """Element-by-element mathematical functions an instrument applies to one candle column."""

    def arc_cosine(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the arc cosine of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `acos` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Take the arc cosine of Infosys's price adjustment factor, which lies between -1 and 1:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.arc_cosine(column="price_factor", days=30)
            print(frame.set_index("datetime")["acos"].tail())
            ```

            Show that a close above 1 has no arc cosine, so every value comes back undefined:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.arc_cosine(days=30)
            missing = frame["acos"].isna().sum()
            print(f"{missing} of {len(frame)} values are undefined")
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
        prices["acos"] = talib.ACOS(prices[column])
        return prices

    def arc_sine(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the arc sine of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `asin` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Take the arc sine of Infosys's price adjustment factor, which lies between -1 and 1:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.arc_sine(column="price_factor", days=30)
            print(frame.set_index("datetime")["asin"].tail())
            ```

            Show that a close above 1 has no arc sine, so every value comes back undefined:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.arc_sine(days=30)
            missing = frame["asin"].isna().sum()
            print(f"{missing} of {len(frame)} values are undefined")
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
        prices["asin"] = talib.ASIN(prices[column])
        return prices

    def arc_tangent(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the arc tangent of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `atan` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five arc tangents of Vodafone Idea's close:

            ```python
            from tradingmachine.assets import equities

            vodafone_idea = equities.Equity(exchange="nse", symbol="IDEA")
            frame = vodafone_idea.arc_tangent(days=30)
            print(frame.set_index("datetime")["atan"].tail())
            ```

            Print the arc tangent of NIFTY's daily low, which is close to pi over two for any large value:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.arc_tangent(column="low", days=30)
            print(frame.set_index("datetime")["atan"].tail())
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
        prices["atan"] = talib.ATAN(prices[column])
        return prices

    def ceiling(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the ceiling of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `ceil` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Vodafone Idea's close rounded up to the next whole rupee:

            ```python
            from tradingmachine.assets import equities

            vodafone_idea = equities.Equity(exchange="nse", symbol="IDEA")
            frame = vodafone_idea.ceiling(days=30)
            columns = [
                "datetime",
                "close",
                "ceil",
            ]
            print(frame[columns].tail())
            ```

            Count the days in the last half year on which Infosys closed on a whole rupee:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.ceiling(days=180)
            whole = (frame["ceil"] == frame["close"]).sum()
            print(f"Closed on a whole rupee on {whole} of {len(frame)} days")
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
        prices["ceil"] = talib.CEIL(prices[column])
        return prices

    def cosine(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the cosine of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `cos` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five cosines of Infosys's close, treated as radians:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.cosine(days=30)
            print(frame.set_index("datetime")["cos"].tail())
            ```

            Take the cosine of Infosys's price adjustment factor:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.cosine(column="price_factor", days=30)
            print(frame.set_index("datetime")["cos"].tail())
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
        prices["cos"] = talib.COS(prices[column])
        return prices

    def hyperbolic_cosine(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the hyperbolic cosine of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `cosh` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five hyperbolic cosines of Vodafone Idea's close:

            ```python
            from tradingmachine.assets import equities

            vodafone_idea = equities.Equity(exchange="nse", symbol="IDEA")
            frame = vodafone_idea.hyperbolic_cosine(days=30)
            print(frame.set_index("datetime")["cosh"].tail())
            ```

            Show that a close in the thousands overflows to infinity:

            ```python
            import numpy
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.hyperbolic_cosine(days=30)
            infinite = numpy.isinf(frame["cosh"]).sum()
            print(f"{infinite} of {len(frame)} values overflowed to infinity")
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
        prices["cosh"] = talib.COSH(prices[column])
        return prices

    def exponential(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the exponential of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `exp` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five exponentials of Vodafone Idea's close:

            ```python
            from tradingmachine.assets import equities

            vodafone_idea = equities.Equity(exchange="nse", symbol="IDEA")
            frame = vodafone_idea.exponential(days=30)
            print(frame.set_index("datetime")["exp"].tail())
            ```

            Check that the natural logarithm of the exponential gives the close back:

            ```python
            import numpy
            from tradingmachine.assets import equities

            vodafone_idea = equities.Equity(exchange="nse", symbol="IDEA")
            frame = vodafone_idea.exponential(days=30)
            error = (numpy.log(frame["exp"]) - frame["close"]).abs().max()
            print(f"Largest round-trip error: {error}")
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
        prices["exp"] = talib.EXP(prices[column])
        return prices

    def floor(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the floor of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `floor` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Vodafone Idea's close rounded down to the whole rupee:

            ```python
            from tradingmachine.assets import equities

            vodafone_idea = equities.Equity(exchange="nse", symbol="IDEA")
            frame = vodafone_idea.floor(days=30)
            columns = [
                "datetime",
                "close",
                "floor",
            ]
            print(frame[columns].tail())
            ```

            Average the paise part of Infosys's close over the last quarter:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.floor(days=90)
            paise = (frame["close"] - frame["floor"]) * 100
            print(f"Average paise part of the close: {paise.mean():.1f}")
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
        prices["floor"] = talib.FLOOR(prices[column])
        return prices

    def natural_logarithm(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the natural logarithm of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `ln` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five natural logarithms of Infosys's close:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.natural_logarithm(days=30)
            print(frame.set_index("datetime")["ln"].tail())
            ```

            Add up NIFTY's daily log returns into its total log return for the last year:

            ```python
            import math
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.natural_logarithm(days=365)
            total_log_return = frame["ln"].diff().sum()
            print(f"Total log return {total_log_return:.4f}")
            print(f"Total return {math.exp(total_log_return) - 1:.2%}")
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
        prices["ln"] = talib.LN(prices[column])
        return prices

    def logarithm_base_10(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the base 10 logarithm of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `log10` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five base 10 logarithms of NIFTY's close:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.logarithm_base_10(days=30)
            print(frame.set_index("datetime")["log10"].tail())
            ```

            Count the digits before the decimal point in the latest close of four shares:

            ```python
            import math
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
                "RELIANCE",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                frame = share.logarithm_base_10(days=10)
                digits = math.floor(frame["log10"].iloc[-1]) + 1
                print(f"{symbol}: {digits} digits")
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
        prices["log10"] = talib.LOG10(prices[column])
        return prices

    def sine(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the sine of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `sin` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five sines of Infosys's close, treated as radians:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.sine(days=30)
            print(frame.set_index("datetime")["sin"].tail())
            ```

            Take the sine of Infosys's price adjustment factor:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.sine(column="price_factor", days=30)
            print(frame.set_index("datetime")["sin"].tail())
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
        prices["sin"] = talib.SIN(prices[column])
        return prices

    def hyperbolic_sine(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the hyperbolic sine of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `sinh` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five hyperbolic sines of Vodafone Idea's close:

            ```python
            from tradingmachine.assets import equities

            vodafone_idea = equities.Equity(exchange="nse", symbol="IDEA")
            frame = vodafone_idea.hyperbolic_sine(days=30)
            print(frame.set_index("datetime")["sinh"].tail())
            ```

            Take the hyperbolic sine of Infosys's price adjustment factor:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.hyperbolic_sine(column="price_factor", days=30)
            print(frame.set_index("datetime")["sinh"].tail())
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
        prices["sinh"] = talib.SINH(prices[column])
        return prices

    def square_root(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the square root of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `sqrt` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five square roots of Infosys's close:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.square_root(days=30)
            print(frame.set_index("datetime")["sqrt"].tail())
            ```

            Print the square root of NIFTY's daily high for a fixed week:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.square_root(
                column="high",
                from_date="2026-09-21",
                to_date="2026-09-25",
            )
            print(frame.set_index("datetime")["sqrt"])
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
        prices["sqrt"] = talib.SQRT(prices[column])
        return prices

    def tangent(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the tangent of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `tan` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five tangents of Infosys's close, treated as radians:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.tangent(days=30)
            print(frame.set_index("datetime")["tan"].tail())
            ```

            Check that the tangent equals the sine divided by the cosine:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            tangent = infosys.tangent(days=30)["tan"].iloc[-1]
            sine = infosys.sine(days=30)["sin"].iloc[-1]
            cosine = infosys.cosine(days=30)["cos"].iloc[-1]
            print(f"tan {tangent:.6f}, sin / cos {sine / cosine:.6f}")
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
        prices["tan"] = talib.TAN(prices[column])
        return prices

    def hyperbolic_tangent(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the hyperbolic tangent of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `tanh` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five hyperbolic tangents of Vodafone Idea's close:

            ```python
            from tradingmachine.assets import equities

            vodafone_idea = equities.Equity(exchange="nse", symbol="IDEA")
            frame = vodafone_idea.hyperbolic_tangent(days=30)
            print(frame.set_index("datetime")["tanh"].tail())
            ```

            Take the hyperbolic tangent of Infosys's price adjustment factor:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.hyperbolic_tangent(
                column="price_factor",
                days=30,
            )
            print(frame.set_index("datetime")["tanh"].tail())
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
        prices["tanh"] = talib.TANH(prices[column])
        return prices
