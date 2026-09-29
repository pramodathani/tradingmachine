"""Price statistics: summaries of an instrument's prices, volumes and returns over a range.

Each method fetches the instrument's candles through `prices` and reduces one column to a number, a summary or a histogram. The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.price_mean(column="close", days=365)
"""

import datetime
from typing import Any

import pandas as pd

from tradingmachine.assets.analysis import price_analysis


class PriceStatistics(price_analysis.PriceAnalysis):
    """Summary statistics of the prices, volumes and returns in an instrument's candles."""

    def price_high(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the highest high in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The highest high as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the highest price Infosys reached in the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.price_high(days=365))
            ```

            Print the highest level of the NIFTY 50 index in the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            year_high = nifty.price_high(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            print(year_high)
            ```

            Print how far each of three banks closed below its one-year high:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                year_high = share.price_high(days=365)
                last_close = share.prices(days=10)["close"].iloc[-1]
                distance = (year_high - last_close) / year_high * 100
                print(f"{symbol}: {distance:.1f}% below {year_high}")
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
        return prices["high"].max()

    def price_low(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the lowest low in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The lowest low as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the lowest price Infosys reached in the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.price_low(days=365))
            ```

            Print the one-year trading range of the NIFTY 50 index as a percentage of its low:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            year_low = nifty.price_low(days=365)
            year_high = nifty.price_high(days=365)
            print(f"Range: {(year_high - year_low) / year_low * 100:.1f}%")
            ```

            Print how far each of three IT shares closed above its one-year low:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                year_low = share.price_low(days=365)
                last_close = share.prices(days=10)["close"].iloc[-1]
                distance = (last_close - year_low) / year_low * 100
                print(f"{symbol}: {distance:.1f}% above {year_low}")
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
        return prices["low"].min()

    def price_mean(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the mean of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The mean as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the average daily close of Infosys over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.price_mean(days=365))
            ```

            Compare the average close of three banks over the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                average = share.price_mean(
                    from_date="2025-01-01",
                    to_date="2025-12-31",
                )
                print(f"{symbol}: {average:.2f}")
            ```

            Print the average daily high of the NIFTY 50 index over the last quarter:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            print(nifty.price_mean(column="high", days=90))
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
        return prices[column].mean()

    def price_median(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the median of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The median as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the median daily close of Infosys over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.price_median(days=365))
            ```

            Print whether each share's mean close sits above or below its median, a hint of which way its prices lean:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "RELIANCE",
                "INFY",
                "HDFCBANK",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                mean = share.price_mean(days=365)
                median = share.price_median(days=365)
                if mean > median:
                    print(f"{symbol}: mean {mean:.2f} > median {median:.2f}")
                else:
                    print(f"{symbol}: mean {mean:.2f} < median {median:.2f}")
            ```

            Print the median daily open of the NIFTY 50 index in the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            print(
                nifty.price_median(
                    column="open",
                    from_date="2025-01-01",
                    to_date="2025-12-31",
                )
            )
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
        return prices[column].median()

    def price_standard_deviation(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the standard deviation of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The standard deviation as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the standard deviation of Infosys's daily close over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.price_standard_deviation(days=365))
            ```

            Compare how widely three shares' prices spread, as a percentage of their mean, so that shares at different prices can be compared:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "RELIANCE",
                "INFY",
                "HDFCBANK",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                spread = share.price_standard_deviation(days=365)
                mean = share.price_mean(days=365)
                print(f"{symbol}: {spread / mean * 100:.1f}% of the mean")
            ```

            Print the standard deviation of an equal-weighted basket of three IT shares, which starts at 100:

            ```python
            from tradingmachine.asset_baskets import watchlist
            from tradingmachine.assets import equities

            information_technology = watchlist.Watchlist(
                name="information technology",
                instruments=[
                    equities.Equity(exchange="nse", symbol="INFY"),
                    equities.Equity(exchange="nse", symbol="TCS"),
                    equities.Equity(exchange="nse", symbol="WIPRO"),
                ],
            )
            print(information_technology.price_standard_deviation(days=365))
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
        return prices[column].std()

    def price_variance(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the variance of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The variance as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the variance of Infosys's daily close over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.price_variance(days=365))
            ```

            Print the variance of each of three banks' closes over the last six months:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                print(f"{symbol}: {share.price_variance(days=182):.2f}")
            ```

            Compare the variance of the NIFTY 50 index's close in 2024 and in 2025:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            years = [
                "2024",
                "2025",
            ]
            for year in years:
                variance = nifty.price_variance(
                    from_date=f"{year}-01-01",
                    to_date=f"{year}-12-31",
                )
                print(f"{year}: {variance:.0f}")
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
        return prices[column].var()

    def price_mean_absolute_deviation(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the mean absolute deviation of one candle column from its mean in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The mean absolute deviation as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the mean absolute deviation of Infosys's daily close over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.price_mean_absolute_deviation(days=365))
            ```

            Compare the mean absolute deviation with the standard deviation for three shares, since a large gap points to a few extreme prices:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "RELIANCE",
                "INFY",
                "HDFCBANK",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                absolute = share.price_mean_absolute_deviation(days=365)
                standard = share.price_standard_deviation(days=365)
                print(f"{symbol}: {absolute:.2f} against {standard:.2f}")
            ```

            Print the mean absolute deviation of the NIFTY 50 index's daily low over the last quarter:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            print(nifty.price_mean_absolute_deviation(column="low", days=90))
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
        deviations = prices[column] - prices[column].mean()
        return deviations.abs().mean()

    def price_skewness(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the skewness of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The skewness as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the skewness of Infosys's daily close over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.price_skewness(days=365))
            ```

            Say for each of three IT shares whether its closes were skewed towards high or low prices over the last year:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                skewness = share.price_skewness(days=365)
                if skewness > 0:
                    print(f"{symbol}: {skewness:.2f}, a tail of high prices")
                else:
                    print(f"{symbol}: {skewness:.2f}, a tail of low prices")
            ```

            Print the skewness of the NIFTY 50 index's close in the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            skewness = nifty.price_skewness(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            print(skewness)
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
        return prices[column].skew()

    def price_kurtosis(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the kurtosis of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The kurtosis as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the excess kurtosis of Infosys's daily close over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.price_kurtosis(days=365))
            ```

            Print the excess kurtosis of three banks' closes, where a positive value means more extreme prices than a normal distribution would give:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                print(f"{symbol}: {share.price_kurtosis(days=365):.2f}")
            ```

            Print the excess kurtosis of the NIFTY 50 index's daily high over the last two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            print(nifty.price_kurtosis(column="high", days=730))
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
        return prices[column].kurtosis()

    def price_quantile(
        self,
        quantile: float = 0.5,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds a quantile of one candle column in the range.

        Args:
            quantile: The float quantile to find, between 0 and 1, where 0.5 is the median.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The quantile as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the close that Infosys stayed below on nine days out of ten over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.price_quantile(quantile=0.9, days=365))
            ```

            Print the lower and upper quartiles of three banks' closes over the last year:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                lower = share.price_quantile(quantile=0.25, days=365)
                upper = share.price_quantile(quantile=0.75, days=365)
                print(f"{symbol}: {lower:.2f} to {upper:.2f}")
            ```

            Print the tenth percentile of the NIFTY 50 index's daily low in the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            print(
                nifty.price_quantile(
                    quantile=0.1,
                    column="low",
                    from_date="2025-01-01",
                    to_date="2025-12-31",
                )
            )
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
        return prices[column].quantile(quantile)

    def price_summary(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.Series | None:
        """Summarises one candle column in the range with count, mean, spread and quartiles.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.Series of summary statistics, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print a summary of Infosys's daily close over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.price_summary(days=365))
            ```

            Print the mean and the range of three IT shares' closes from their summaries:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                summary = share.price_summary(days=365)
                print(
                    f"{symbol}: mean {summary['mean']:.2f},"
                    f" from {summary['min']} to {summary['max']}"
                )
            ```

            Print a summary of the NIFTY 50 index's daily high in the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            print(
                nifty.price_summary(
                    column="high",
                    from_date="2025-01-01",
                    to_date="2025-12-31",
                )
            )
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
        return prices[column].describe()

    def price_histogram(
        self,
        bins: int = 50,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> Any:
        """Draws a histogram of one candle column in the range with matplotlib.

        Args:
            bins: The int number of histogram bins.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The matplotlib Axes the histogram was drawn on, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Draw a histogram of Infosys's daily close over the last year and save it as an image:

            ```python
            import pathlib
            import tempfile

            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            axes = infosys.price_histogram(bins=30, days=365)
            path = pathlib.Path(tempfile.gettempdir()) / "infosys_closes.png"
            axes.figure.savefig(path)
            print(f"Saved {len(axes.patches)} bars to {path}")
            ```

            Find the price band where the NIFTY 50 index closed most often in the last year:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            axes = nifty.price_histogram(bins=20, days=365)
            tallest_bar = axes.patches[0]
            for bar in axes.patches:
                if bar.get_height() > tallest_bar.get_height():
                    tallest_bar = bar
            lower = tallest_bar.get_x()
            upper = lower + tallest_bar.get_width()
            count = tallest_bar.get_height()
            print(f"{count:.0f} closes from {lower:.0f} to {upper:.0f}")
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
        return prices[column].hist(bins=bins)

    def volumes(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Fetches the traded volume of each candle in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame with `exchange`, `segment`, `datetime`, `interval` and `volume` columns, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the traded volume of Infosys in each of the last ten days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volumes(days=10))
            ```

            Find the day Reliance Industries traded the most shares in the last year:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            volumes = reliance.volumes(days=365)
            busiest_row = volumes.loc[volumes["volume"].idxmax()]
            busiest_date = busiest_row["datetime"]
            print(f"{busiest_date:%Y-%m-%d}: {busiest_row['volume']}")
            ```

            Compare the last session's volume with the average of the twenty before it for three banks:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                volumes = share.volumes(days=45)["volume"]
                average = volumes.iloc[-21:-1].mean()
                ratio = volumes.iloc[-1] / average
                print(f"{symbol}: {ratio:.2f} times the average")
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
        return prices[
            [
                "exchange",
                "segment",
                "datetime",
                "interval",
                "volume",
            ]
        ]

    def volume_total(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the total volume traded in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The total volume as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print how many Infosys shares changed hands in the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_total(days=365))
            ```

            Compare the total volume of three banks in the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                total = share.volume_total(
                    from_date="2025-01-01",
                    to_date="2025-12-31",
                )
                print(f"{symbol}: {total:,}")
            ```

            Print Infosys's share of the combined volume of three IT shares over the last month:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            totals = {}
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                totals[symbol] = share.volume_total(days=30)
            combined = sum(totals.values())
            share_of_total = totals["INFY"] / combined * 100
            print(f"INFY: {share_of_total:.1f}% of {combined:,}")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].sum()

    def volume_high(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the highest volume of any candle in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The highest volume as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the largest daily volume of Infosys in the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_high(days=365))
            ```

            Print how many times its average day each share's busiest day in the last year was:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "RELIANCE",
                "INFY",
                "HDFCBANK",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                busiest = share.volume_high(days=365)
                average = share.volume_mean(days=365)
                print(f"{symbol}: {busiest / average:.1f} times the average")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].max()

    def volume_low(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the lowest volume of any candle in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The lowest volume as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the smallest daily volume of Infosys in the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_low(days=365))
            ```

            Print the quietest and busiest day's volume of three banks over the last quarter:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                quietest = share.volume_low(days=90)
                busiest = share.volume_high(days=90)
                print(f"{symbol}: from {quietest:,} to {busiest:,}")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].min()

    def volume_mean(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the mean volume per candle in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The mean volume as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the average daily volume of Infosys over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_mean(days=365))
            ```

            Compare each share's average volume in the last month with its average over the last year:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                month = share.volume_mean(days=30)
                year = share.volume_mean(days=365)
                print(f"{symbol}: {month / year:.2f} times the yearly average")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].mean()

    def volume_median(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the median volume per candle in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The median volume as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the median daily volume of Infosys over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_median(days=365))
            ```

            Compare the mean and median volume of three shares, since a mean far above the median points to a few very busy days:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "RELIANCE",
                "INFY",
                "HDFCBANK",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                mean = share.volume_mean(days=365)
                median = share.volume_median(days=365)
                print(f"{symbol}: mean {mean / median:.2f} times the median")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].median()

    def volume_standard_deviation(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the standard deviation of volume per candle in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The standard deviation as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the standard deviation of Infosys's daily volume over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_standard_deviation(days=365))
            ```

            Compare how erratic three banks' volumes are, as the standard deviation over the mean:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                spread = share.volume_standard_deviation(days=365)
                mean = share.volume_mean(days=365)
                print(f"{symbol}: {spread / mean:.2f}")
            ```

            Flag Infosys's last session when its volume was more than two standard deviations above the mean:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            mean = infosys.volume_mean(days=365)
            spread = infosys.volume_standard_deviation(days=365)
            last_volume = infosys.volumes(days=10)["volume"].iloc[-1]
            if last_volume > mean + 2 * spread:
                print(f"Unusually busy: {last_volume:,}")
            else:
                print(f"Ordinary: {last_volume:,}")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].std()

    def volume_variance(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the variance of volume per candle in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The variance as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the variance of Infosys's daily volume over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_variance(days=365))
            ```

            Print the variance of three IT shares' daily volume in the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                variance = share.volume_variance(
                    from_date="2025-01-01",
                    to_date="2025-12-31",
                )
                print(f"{symbol}: {variance:.3e}")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].var()

    def volume_mean_absolute_deviation(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the mean absolute deviation of volume per candle from its mean in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The mean absolute deviation as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the mean absolute deviation of Infosys's daily volume over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_mean_absolute_deviation(days=365))
            ```

            Print how far a typical day's volume strays from the average, as a percentage of it, for three shares:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "RELIANCE",
                "INFY",
                "HDFCBANK",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                deviation = share.volume_mean_absolute_deviation(days=365)
                mean = share.volume_mean(days=365)
                print(f"{symbol}: {deviation / mean * 100:.0f}%")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        deviations = volumes["volume"] - volumes["volume"].mean()
        return deviations.abs().mean()

    def volume_kurtosis(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the kurtosis of volume per candle in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The kurtosis as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the excess kurtosis of Infosys's daily volume over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_kurtosis(days=365))
            ```

            Print which of three banks has the heaviest tail of very busy or very quiet days:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                print(f"{symbol}: {share.volume_kurtosis(days=365):.2f}")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].kurtosis()

    def volume_skewness(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the skewness of volume per candle in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The skewness as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the skewness of Infosys's daily volume over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_skewness(days=365))
            ```

            Print the skewness of three IT shares' daily volume, where a large positive value means occasional very busy days:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                print(f"{symbol}: {share.volume_skewness(days=365):.2f}")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].skew()

    def volume_quantile(
        self,
        quantile: float = 0.5,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds a quantile of volume per candle in the range.

        Args:
            quantile: The float quantile to find, between 0 and 1, where 0.5 is the median.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The quantile as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the volume Infosys stayed below on nine days out of ten over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_quantile(quantile=0.9, days=365))
            ```

            Count the days in the last year when Reliance Industries traded above its ninetieth percentile volume:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            threshold = reliance.volume_quantile(quantile=0.9, days=365)
            volumes = reliance.volumes(days=365)["volume"]
            busy_days = 0
            for volume in volumes:
                if volume > threshold:
                    busy_days += 1
            print(f"{busy_days} days above {threshold:,.0f}")
            ```

            Print the median and the lower quartile of three banks' daily volume:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                lower = share.volume_quantile(quantile=0.25, days=365)
                median = share.volume_quantile(quantile=0.5, days=365)
                print(f"{symbol}: {lower:,.0f} and {median:,.0f}")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].quantile(quantile)

    def volume_summary(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.Series | None:
        """Summarises volume per candle in the range with count, mean, spread and quartiles.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.Series of summary statistics, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print a summary of Infosys's daily volume over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.volume_summary(days=365))
            ```

            Print the average and the busiest day of three IT shares from their volume summaries:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                summary = share.volume_summary(days=365)
                average = summary["mean"]
                busiest = summary["max"]
                print(f"{symbol}: {average:,.0f}, at most {busiest:,.0f}")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].describe()

    def volume_histogram(
        self,
        bins: int = 50,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> Any:
        """Draws a histogram of volume per candle in the range with matplotlib.

        Args:
            bins: The int number of histogram bins.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The matplotlib Axes the histogram was drawn on, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Draw a histogram of Infosys's daily volume over the last year and save it as an image:

            ```python
            import pathlib
            import tempfile

            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            axes = infosys.volume_histogram(bins=40, days=365)
            path = pathlib.Path(tempfile.gettempdir()) / "infosys_volumes.png"
            axes.figure.savefig(path)
            print(f"Saved {len(axes.patches)} bars to {path}")
            ```

            Find the volume band that Reliance Industries traded in most often in the last year:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            axes = reliance.volume_histogram(bins=20, days=365)
            tallest_bar = axes.patches[0]
            for bar in axes.patches:
                if bar.get_height() > tallest_bar.get_height():
                    tallest_bar = bar
            lower = tallest_bar.get_x()
            upper = lower + tallest_bar.get_width()
            count = tallest_bar.get_height()
            print(f"{count:.0f} days from {lower:,.0f} to {upper:,.0f}")
            ```
        """
        volumes = self.volumes(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if volumes is None:
            return None
        return volumes["volume"].hist(bins=bins)

    def returns(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Calculates the fractional change of one candle column from each candle to the next.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame with `exchange`, `segment`, `datetime`, `interval` and `returns` columns, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's daily returns over the last ten days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns(days=10))
            ```

            Compound the NIFTY 50 index's daily returns into its return over the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            returns = nifty.returns(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            growth = 1.0
            for daily_return in returns["returns"].dropna():
                growth = growth * (1 + daily_return)
            print(f"{(growth - 1) * 100:.2f}%")
            ```

            Print the daily returns of an equal-weighted basket of three IT shares over the last ten days:

            ```python
            from tradingmachine.asset_baskets import watchlist
            from tradingmachine.assets import equities

            information_technology = watchlist.Watchlist(
                name="information technology",
                instruments=[
                    equities.Equity(exchange="nse", symbol="INFY"),
                    equities.Equity(exchange="nse", symbol="TCS"),
                    equities.Equity(exchange="nse", symbol="WIPRO"),
                ],
            )
            print(information_technology.returns(days=10))
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
        prices["returns"] = prices[column].pct_change()
        return prices[
            [
                "exchange",
                "segment",
                "datetime",
                "interval",
                "returns",
            ]
        ]

    def returns_high(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the highest return of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The highest return as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's best daily return in the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns_high(days=365))
            ```

            Print each bank's best day in the last year as a percentage:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                print(f"{symbol}: {share.returns_high(days=365) * 100:.2f}%")
            ```

            Print the NIFTY 50 index's largest rise from one day's high to the next in the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            best = nifty.returns_high(
                column="high",
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            print(f"{best * 100:.2f}%")
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        return returns["returns"].max()

    def returns_low(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the lowest return of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The lowest return as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's worst daily return in the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns_low(days=365))
            ```

            Print the worst and the best day of three IT shares in the last year:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                worst = share.returns_low(days=365) * 100
                best = share.returns_high(days=365) * 100
                print(f"{symbol}: from {worst:.2f}% to {best:.2f}%")
            ```

            Print the NIFTY 50 index's worst day in the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            worst = nifty.returns_low(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            print(f"{worst * 100:.2f}%")
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        return returns["returns"].min()

    def returns_mean(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the mean return of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The mean return as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's average daily return over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns_mean(days=365))
            ```

            Annualise the average daily return of three shares by multiplying it by 252 trading days:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "RELIANCE",
                "INFY",
                "HDFCBANK",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                annual = share.returns_mean(days=365) * 252
                print(f"{symbol}: {annual * 100:.1f}% a year")
            ```

            Print the average daily return of an equal-weighted basket of three IT shares:

            ```python
            from tradingmachine.asset_baskets import watchlist
            from tradingmachine.assets import equities

            information_technology = watchlist.Watchlist(
                name="information technology",
                instruments=[
                    equities.Equity(exchange="nse", symbol="INFY"),
                    equities.Equity(exchange="nse", symbol="TCS"),
                    equities.Equity(exchange="nse", symbol="WIPRO"),
                ],
            )
            print(information_technology.returns_mean(days=365))
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        return returns["returns"].mean()

    def returns_median(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the median return of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The median return as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's median daily return over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns_median(days=365))
            ```

            Compare the median and mean daily return of three banks, since a mean below the median points to a few large falls:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                median = share.returns_median(days=365)
                mean = share.returns_mean(days=365)
                print(f"{symbol}: median {median:.5f}, mean {mean:.5f}")
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        return returns["returns"].median()

    def returns_standard_deviation(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the standard deviation of returns of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The standard deviation as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the standard deviation of Infosys's daily returns over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns_standard_deviation(days=365))
            ```

            Annualise the volatility of three shares by multiplying the daily standard deviation by the square root of 252:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "RELIANCE",
                "INFY",
                "HDFCBANK",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                daily = share.returns_standard_deviation(days=365)
                annual = daily * 252**0.5
                print(f"{symbol}: {annual * 100:.1f}% a year")
            ```

            Compare the volatility of an equal-weighted basket of three IT shares with that of Infosys alone:

            ```python
            from tradingmachine.asset_baskets import watchlist
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            information_technology = watchlist.Watchlist(
                name="information technology",
                instruments=[
                    infosys,
                    equities.Equity(exchange="nse", symbol="TCS"),
                    equities.Equity(exchange="nse", symbol="WIPRO"),
                ],
            )
            basket = information_technology.returns_standard_deviation(days=365)
            single = infosys.returns_standard_deviation(days=365)
            print(f"Basket {basket:.4f} against Infosys {single:.4f}")
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        return returns["returns"].std()

    def returns_variance(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the variance of returns of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The variance as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the variance of Infosys's daily returns over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns_variance(days=365))
            ```

            Print the annualised variance of three banks' daily returns:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                print(f"{symbol}: {share.returns_variance(days=365) * 252:.4f}")
            ```

            Compare the variance of the NIFTY 50 index's daily returns in 2024 and in 2025:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            years = [
                "2024",
                "2025",
            ]
            for year in years:
                variance = nifty.returns_variance(
                    from_date=f"{year}-01-01",
                    to_date=f"{year}-12-31",
                )
                print(f"{year}: {variance:.6f}")
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        return returns["returns"].var()

    def returns_mean_absolute_deviation(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the mean absolute deviation of returns of one candle column from their mean in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The mean absolute deviation as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the mean absolute deviation of Infosys's daily returns over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns_mean_absolute_deviation(days=365))
            ```

            Print how far a typical day's return strays from the average for three IT shares, in percent:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                deviation = share.returns_mean_absolute_deviation(days=365)
                print(f"{symbol}: {deviation * 100:.2f}%")
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        deviations = returns["returns"] - returns["returns"].mean()
        return deviations.abs().mean()

    def returns_skewness(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the skewness of returns of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The skewness as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the skewness of Infosys's daily returns over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns_skewness(days=365))
            ```

            Say for each of three shares whether its large moves were more often rises or falls:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "RELIANCE",
                "INFY",
                "HDFCBANK",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                skewness = share.returns_skewness(days=365)
                if skewness > 0:
                    print(f"{symbol}: {skewness:.2f}, more large rises")
                else:
                    print(f"{symbol}: {skewness:.2f}, more large falls")
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        return returns["returns"].skew()

    def returns_kurtosis(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the kurtosis of returns of one candle column in the range.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The kurtosis as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the excess kurtosis of Infosys's daily returns over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns_kurtosis(days=365))
            ```

            Print the excess kurtosis of three banks' daily returns, where a high value means more extreme days than a normal distribution would give:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                print(f"{symbol}: {share.returns_kurtosis(days=365):.2f}")
            ```

            Print the excess kurtosis of the NIFTY 50 index's daily returns over the last two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            print(nifty.returns_kurtosis(days=730))
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        return returns["returns"].kurt()

    def returns_quantile(
        self,
        quantile: float = 0.5,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds a quantile of returns of one candle column in the range.

        Args:
            quantile: The float quantile to find, between 0 and 1, where 0.5 is the median.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The quantile as a float, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the daily return Infosys fell below on one day in twenty over the last year, a simple historical value at risk:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns_quantile(quantile=0.05, days=365))
            ```

            Print the loss on a Rs 1,00,000 holding of each bank on its worst day in twenty:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                fifth_percentile = share.returns_quantile(
                    quantile=0.05,
                    days=365,
                )
                print(f"{symbol}: Rs {-fifth_percentile * 100000:,.0f}")
            ```

            Print the NIFTY 50 index's ninety-fifth percentile daily return in the calendar year 2025:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            print(
                nifty.returns_quantile(
                    quantile=0.95,
                    from_date="2025-01-01",
                    to_date="2025-12-31",
                )
            )
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        return returns["returns"].quantile(q=quantile)

    def returns_histogram(
        self,
        bins: int = 50,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> Any:
        """Draws a histogram of returns of one candle column in the range with matplotlib.

        Args:
            bins: The int number of histogram bins.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The matplotlib Axes the histogram was drawn on, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Draw a histogram of Infosys's daily returns over the last year and save it as an image:

            ```python
            import pathlib
            import tempfile

            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            axes = infosys.returns_histogram(bins=40, days=365)
            path = pathlib.Path(tempfile.gettempdir()) / "infosys_returns.png"
            axes.figure.savefig(path)
            print(f"Saved {len(axes.patches)} bars to {path}")
            ```

            Count how many of the NIFTY 50 index's daily returns in the last year fell in bars below zero:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            axes = nifty.returns_histogram(bins=30, days=365)
            falling_days = 0
            for bar in axes.patches:
                if bar.get_x() + bar.get_width() <= 0:
                    falling_days += bar.get_height()
            print(f"{falling_days:.0f} days in bars wholly below zero")
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        return returns["returns"].hist(bins=bins)

    def returns_summary(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.Series | None:
        """Summarises returns of one candle column in the range with count, mean, spread and quartiles.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.Series of summary statistics, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print a summary of Infosys's daily returns over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            print(infosys.returns_summary(days=365))
            ```

            Print the average, spread and worst day of three banks from their return summaries:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                summary = share.returns_summary(days=365)
                print(
                    f"{symbol}: mean {summary['mean']:.4f},"
                    f" deviation {summary['std']:.4f},"
                    f" worst {summary['min']:.4f}"
                )
            ```

            Print a summary of the daily returns of an equal-weighted basket of three IT shares:

            ```python
            from tradingmachine.asset_baskets import watchlist
            from tradingmachine.assets import equities

            information_technology = watchlist.Watchlist(
                name="information technology",
                instruments=[
                    equities.Equity(exchange="nse", symbol="INFY"),
                    equities.Equity(exchange="nse", symbol="TCS"),
                    equities.Equity(exchange="nse", symbol="WIPRO"),
                ],
            )
            print(information_technology.returns_summary(days=365))
            ```
        """
        returns = self.returns(
            column=column,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if returns is None:
            return None
        return returns["returns"].describe()
