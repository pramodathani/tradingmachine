"""Statistic functions: rolling regressions, correlations and dispersion from TA-Lib.

Each method fetches the instrument's candles through `prices`, adds one or more TA-Lib columns and returns the candles. The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.linear_regression_slope(window=14, days=365)
  nifty = instruments.NonTradeableInstrument(exchange="nse", segment="equity_indices", symbol="NIFTY")
  frame = infosys.beta(nifty, window=60, days=730)
"""

import datetime

import pandas as pd
import talib

from tradingmachine.assets.analysis import price_analysis


class StatisticFunctions(price_analysis.PriceAnalysis):
    """Rolling statistics an instrument calculates from its candles with TA-Lib."""

    def beta(
        self,
        benchmark: price_analysis.PriceAnalysis,
        window: int = 14,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the rolling beta of the instrument against a benchmark, such as an index.

        TA-Lib's beta works on the change from each candle to the next, so a beta of 1 means the instrument moved in step with the benchmark. Candles are matched by time, and a candle either side lacks is left out.

        Args:
            benchmark: The instrument to measure against, such as an tradingmachine.assets.instruments.NonTradeableInstrument for NIFTY, or any other object with a `prices` method.
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use from both, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the matched candles with a `benchmark_<column>` column and a `beta_<window>` column added, or None when UBI has no candles for either instrument in the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 20-day beta against NIFTY:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = infosys.beta(benchmark=nifty, window=20, days=180)
            print(frame.set_index("datetime")["beta_20"].tail())
            ```

            Compare four shares by their 60-day beta against NIFTY:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
                "RELIANCE",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                frame = share.beta(benchmark=nifty, window=60, days=365)
                print(f"{symbol}: beta {frame['beta_60'].iloc[-1]:.2f}")
            ```
        """
        prices = self._prices_with_benchmark(
            benchmark=benchmark,
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if prices is None:
            return None
        prices[f"beta_{window}"] = talib.BETA(
            prices[f"benchmark_{column}"],
            prices[column],
            timeperiod=window,
        )
        return prices

    def correlation_coefficient(
        self,
        benchmark: price_analysis.PriceAnalysis,
        window: int = 14,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the rolling Pearson correlation of the instrument's returns with a benchmark's returns.

        Returns, the fractional change from each candle to the next, are correlated rather than price levels, because two unrelated prices that both trend upwards would otherwise look strongly correlated. Candles are matched by time, and a candle either side lacks is left out.

        Args:
            benchmark: The instrument to compare with, such as an tradingmachine.assets.instruments.NonTradeableInstrument for NIFTY, or any other object with a `prices` method.
            window: The int number of returns in each calculation window.
            column: The str name of the candle column to use from both, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the matched candles with a `benchmark_<column>` column and a `corr_<window>` column added, which lies between -1 and 1, or None when UBI has no candles for either instrument in the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 20-day correlation with NIFTY:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = infosys.correlation_coefficient(
                benchmark=nifty,
                window=20,
                days=180,
            )
            print(frame.set_index("datetime")["corr_20"].tail())
            ```

            Average the 30-day correlation of TCS with Infosys over the last year, using a share as the benchmark:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = tcs.correlation_coefficient(
                benchmark=infosys,
                window=30,
                days=365,
            )
            print(f"Average correlation: {frame['corr_30'].mean():.2f}")
            ```
        """
        prices = self._prices_with_benchmark(
            benchmark=benchmark,
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if prices is None:
            return None
        prices[f"corr_{window}"] = talib.CORREL(
            prices[column].pct_change(),
            prices[f"benchmark_{column}"].pct_change(),
            timeperiod=window,
        )
        return prices

    def _prices_with_benchmark(
        self,
        benchmark: price_analysis.PriceAnalysis,
        column: str,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Fetches the instrument's candles with a benchmark's column matched to them by time.

        Args:
            benchmark: The object with a `prices` method whose column is matched in.
            column: The str name of the candle column taken from the benchmark.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the instrument's candles that have a benchmark candle at the same time, with an added `benchmark_<column>` column, or None when either has no candles in the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
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
        benchmark_prices = benchmark.prices(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if benchmark_prices is None:
            return None
        benchmark_column = benchmark_prices[
            [
                "datetime",
                column,
            ]
        ].rename(columns={column: f"benchmark_{column}"})
        matched = prices.merge(benchmark_column, on="datetime", how="inner")
        if matched.empty:
            return None
        return matched

    def linear_regression(
        self,
        window: int = 14,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the end value of a rolling linear regression line through one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `lin_regr_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five end values of Infosys's 14-day regression line:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.linear_regression(days=90)
            print(frame.set_index("datetime")["lin_regr_14"].tail())
            ```

            Print how far NIFTY's close sits from its 20-day regression line:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.linear_regression(window=20, days=120)
            gap = frame["close"].iloc[-1] - frame["lin_regr_20"].iloc[-1]
            print(f"The close is {gap:.2f} points from the regression line")
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
        prices[f"lin_regr_{window}"] = talib.LINEARREG(
            prices[column], timeperiod=window
        )
        return prices

    def linear_regression_slope(
        self,
        window: int = 14,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the slope of a rolling linear regression line through one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `lin_regr_slope_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five slopes of Infosys's 14-day regression line:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.linear_regression_slope(days=90)
            print(frame.set_index("datetime")["lin_regr_slope_14"].tail())
            ```

            Say whether NIFTY's 50-day regression line is rising or falling:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.linear_regression_slope(window=50, days=180)
            slope = frame["lin_regr_slope_50"].iloc[-1]
            if slope > 0:
                print(f"Rising by {slope:.2f} points a day")
            else:
                print(f"Falling by {-slope:.2f} points a day")
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
        prices[f"lin_regr_slope_{window}"] = talib.LINEARREG_SLOPE(
            prices[column], timeperiod=window
        )
        return prices

    def linear_regression_intercept(
        self,
        window: int = 14,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the intercept of a rolling linear regression line through one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `lin_regr_int_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five intercepts of Infosys's 14-day regression line:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.linear_regression_intercept(days=90)
            print(frame.set_index("datetime")["lin_regr_int_14"].tail())
            ```

            Rebuild the line's end value from its intercept and slope and compare it with linear_regression:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            intercept_frame = infosys.linear_regression_intercept(days=90)
            slope_frame = infosys.linear_regression_slope(days=90)
            line_frame = infosys.linear_regression(days=90)
            intercept = intercept_frame["lin_regr_int_14"].iloc[-1]
            slope = slope_frame["lin_regr_slope_14"].iloc[-1]
            print(f"Rebuilt end value {intercept + 13 * slope:.2f}")
            print(f"linear_regression {line_frame['lin_regr_14'].iloc[-1]:.2f}")
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
        prices[f"lin_regr_int_{window}"] = talib.LINEARREG_INTERCEPT(
            prices[column], timeperiod=window
        )
        return prices

    def linear_regression_angle(
        self,
        window: int = 14,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the angle in degrees of a rolling linear regression line through one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `lin_regr_angle_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five angles of Infosys's 14-day regression line:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.linear_regression_angle(days=90)
            print(frame.set_index("datetime")["lin_regr_angle_14"].tail())
            ```

            Print the angle of NIFTY's 30-day regression line in degrees:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.linear_regression_angle(window=30, days=120)
            print(f"{frame['lin_regr_angle_30'].iloc[-1]:.2f} degrees")
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
        prices[f"lin_regr_angle_{window}"] = talib.LINEARREG_ANGLE(
            prices[column], timeperiod=window
        )
        return prices

    def standard_deviation(
        self,
        window: int = 14,
        standard_deviations: float = 1,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the rolling standard deviation of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            standard_deviations: The float multiple of the standard deviation to report.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `std_dev_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 20-day standard deviation of the close:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.standard_deviation(window=20, days=90)
            print(frame.set_index("datetime")["std_dev_20"].tail())
            ```

            Draw NIFTY's upper and lower bands two standard deviations from its 20-day average:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.standard_deviation(
                window=20,
                standard_deviations=2,
                days=90,
            )
            middle = frame["close"].rolling(20).mean().iloc[-1]
            width = frame["std_dev_20"].iloc[-1]
            print(f"Upper {middle + width:.2f}, lower {middle - width:.2f}")
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
        prices[f"std_dev_{window}"] = talib.STDDEV(
            prices[column],
            timeperiod=window,
            nbdev=standard_deviations,
        )
        return prices

    def variance(
        self,
        window: int = 14,
        standard_deviations: float = 1,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the rolling variance of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            standard_deviations: The float multiple passed to TA-Lib, which its variance calculation does not use.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `var_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 20-day variance of the close:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.variance(window=20, days=90)
            print(frame.set_index("datetime")["var_20"].tail())
            ```

            Find the day in the first half of 2026 on which NIFTY's 10-day variance peaked:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.variance(
                window=10,
                from_date="2026-01-01",
                to_date="2026-06-30",
            )
            peak_row = frame["var_10"].idxmax()
            peak_day = frame.loc[peak_row, "datetime"].date()
            print(peak_day, round(frame["var_10"].max(), 1))
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
        prices[f"var_{window}"] = talib.VAR(
            prices[column],
            timeperiod=window,
            nbdev=standard_deviations,
        )
        return prices
