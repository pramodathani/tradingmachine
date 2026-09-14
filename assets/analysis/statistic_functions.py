"""Statistic functions: rolling regressions, correlations and dispersion from TA-Lib.

Each method fetches the instrument's candles through `prices`, adds one or more TA-Lib columns and returns the candles. The class is inherited by `assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.linear_regression_slope(window=14, days=365)
  nifty = instruments.NonTradeableInstrument(exchange="nse", segment="equity_indices", symbol="NIFTY")
  frame = infosys.beta(nifty, window=60, days=730)
"""

import datetime

import pandas as pd
import talib

from assets.analysis import price_analysis


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
            benchmark: The instrument to measure against, such as an assets.instruments.NonTradeableInstrument for NIFTY, or any other object with a `prices` method.
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
            benchmark: The instrument to compare with, such as an assets.instruments.NonTradeableInstrument for NIFTY, or any other object with a `prices` method.
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
