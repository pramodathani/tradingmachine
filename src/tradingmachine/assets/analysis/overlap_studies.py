"""Overlap studies: moving averages, bands and other indicators drawn on the price scale.

Each method fetches the instrument's candles through `prices`, adds one or more TA-Lib columns and returns the candles. The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.simple_moving_average(window=20, days=365)
"""

import datetime

import pandas as pd
import talib

from tradingmachine.assets.analysis import price_analysis


class OverlapStudies(price_analysis.PriceAnalysis):
    """Moving averages, Bollinger bands and other indicators an instrument draws over its candles."""

    def simple_moving_average(
        self,
        window: int = 10,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the simple moving average of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with an `sma_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's close and its twenty-day simple moving average for the last five days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.simple_moving_average(window=20, days=90)
            print(candles[["datetime", "close", "sma_20"]].tail())
            ```

            Check whether the NIFTY 50 index's fifty-day average is above its two-hundred-day average, the golden cross:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            fast = nifty.simple_moving_average(window=50, days=400)
            slow = nifty.simple_moving_average(window=200, days=400)
            fast_average = fast["sma_50"].iloc[-1]
            slow_average = slow["sma_200"].iloc[-1]
            if fast_average > slow_average:
                print(f"Golden cross: {fast_average:.0f} > {slow_average:.0f}")
            else:
                print(f"Death cross: {fast_average:.0f} < {slow_average:.0f}")
            ```

            Print the ten-day average of an equal-weighted basket of three IT shares:

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
            candles = information_technology.simple_moving_average(days=60)
            print(candles[["datetime", "close", "sma_10"]].tail())
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
        prices[f"sma_{window}"] = talib.SMA(prices[column], timeperiod=window)
        return prices

    def exponential_moving_average(
        self,
        window: int = 10,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the exponential moving average of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with an `ema_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's close and its twenty-day exponential moving average for the last five days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.exponential_moving_average(window=20, days=120)
            print(candles[["datetime", "close", "ema_20"]].tail())
            ```

            Print the gap between the twelve-day and twenty-six-day averages of three banks, the line MACD is built on:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                fast = share.exponential_moving_average(window=12, days=180)
                slow = share.exponential_moving_average(window=26, days=180)
                gap = fast["ema_12"].iloc[-1] - slow["ema_26"].iloc[-1]
                print(f"{symbol}: {gap:.2f}")
            ```

            Print how far the NIFTY 50 index closed from its fifty-day exponential average:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            candles = nifty.exponential_moving_average(window=50, days=250)
            last_row = candles.iloc[-1]
            distance = (last_row["close"] / last_row["ema_50"] - 1) * 100
            print(f"{distance:.2f}% from the average")
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
        prices[f"ema_{window}"] = talib.EMA(prices[column], timeperiod=window)
        return prices

    def bollinger_bands(
        self,
        window: int = 10,
        standard_deviations_up: float = 2,
        standard_deviations_down: float = 2,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the upper, middle and lower Bollinger bands of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            standard_deviations_up: The float number of standard deviations from the middle band to the upper band.
            standard_deviations_down: The float number of standard deviations from the middle band to the lower band.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `bb_upper_<window>`, `bb_middle_<window>` and `bb_lower_<window>` columns added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's twenty-day Bollinger Bands for the last five days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.bollinger_bands(window=20, days=120)
            columns = [
                "datetime",
                "close",
                "bb_lower_20",
                "bb_middle_20",
                "bb_upper_20",
            ]
            print(candles[columns].tail())
            ```

            Print where three shares closed within their bands, from 0 at the lower band to 1 at the upper:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "RELIANCE",
                "INFY",
                "HDFCBANK",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                last_row = share.bollinger_bands(window=20, days=120).iloc[-1]
                width = last_row["bb_upper_20"] - last_row["bb_lower_20"]
                position = (last_row["close"] - last_row["bb_lower_20"]) / width
                print(f"{symbol}: {position:.2f}")
            ```

            Print the width of the NIFTY 50 index's bands with three standard deviations, as a percentage of the middle band:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            candles = nifty.bollinger_bands(
                window=20,
                standard_deviations_up=3,
                standard_deviations_down=3,
                days=120,
            )
            last_row = candles.iloc[-1]
            width = last_row["bb_upper_20"] - last_row["bb_lower_20"]
            print(f"{width / last_row['bb_middle_20'] * 100:.2f}%")
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
        upper, middle, lower = talib.BBANDS(
            prices[column],
            timeperiod=window,
            nbdevup=standard_deviations_up,
            nbdevdn=standard_deviations_down,
        )
        prices[f"bb_upper_{window}"] = upper
        prices[f"bb_middle_{window}"] = middle
        prices[f"bb_lower_{window}"] = lower
        return prices

    def weighted_moving_average(
        self,
        window: int = 10,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the weighted moving average of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `wma_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's close and its twenty-day weighted moving average for the last five days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.weighted_moving_average(window=20, days=90)
            print(candles[["datetime", "close", "wma_20"]].tail())
            ```

            Compare the weighted and simple ten-day averages of the NIFTY 50 index, since the weighted one reacts faster to the latest closes:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            weighted = nifty.weighted_moving_average(window=10, days=60)
            simple = nifty.simple_moving_average(window=10, days=60)
            print(f"Weighted {weighted['wma_10'].iloc[-1]:.2f}")
            print(f"Simple {simple['sma_10'].iloc[-1]:.2f}")
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
        prices[f"wma_{window}"] = talib.WMA(prices[column], timeperiod=window)
        return prices

    def double_exponential_moving_average(
        self,
        window: int = 10,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the double exponential moving average of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `dema_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's close and its twenty-day double exponential moving average:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.double_exponential_moving_average(
                window=20,
                days=180,
            )
            print(candles[["datetime", "close", "dema_20"]].tail())
            ```

            Print whether three banks closed above their double exponential average:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                candles = share.double_exponential_moving_average(days=120)
                last_row = candles.iloc[-1]
                if last_row["close"] > last_row["dema_10"]:
                    print(f"{symbol}: above")
                else:
                    print(f"{symbol}: below")
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
        prices[f"dema_{window}"] = talib.DEMA(prices[column], timeperiod=window)
        return prices

    def triple_exponential_moving_average(
        self,
        window: int = 10,
        volume_factor: float = 0.7,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds Tillson's T3 triple exponential moving average of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            volume_factor: The float volume factor that sets how strongly T3 smooths, between 0 and 1.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `t3_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's close and its ten-day Tillson T3 average:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.triple_exponential_moving_average(
                window=10,
                days=180,
            )
            print(candles[["datetime", "close", "t3_10"]].tail())
            ```

            Compare a smoother and a more responsive T3 average of the NIFTY 50 index by changing the volume factor:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            smooth = nifty.triple_exponential_moving_average(
                window=10,
                volume_factor=0.9,
                days=250,
            )
            responsive = nifty.triple_exponential_moving_average(
                window=10,
                volume_factor=0.3,
                days=250,
            )
            print(f"Factor 0.9: {smooth['t3_10'].iloc[-1]:.2f}")
            print(f"Factor 0.3: {responsive['t3_10'].iloc[-1]:.2f}")
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
        prices[f"t3_{window}"] = talib.T3(
            prices[column],
            timeperiod=window,
            vfactor=volume_factor,
        )
        return prices

    def kaufman_adaptive_moving_average(
        self,
        window: int = 10,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Kaufman adaptive moving average of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `kama_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's close and its ten-day Kaufman adaptive moving average:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.kaufman_adaptive_moving_average(days=120)
            print(candles[["datetime", "close", "kama_10"]].tail())
            ```

            Print whether the Kaufman average of three IT shares rose over the last five days:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                candles = share.kaufman_adaptive_moving_average(
                    window=20,
                    days=180,
                )
                average = candles["kama_20"]
                change = average.iloc[-1] - average.iloc[-6]
                if change > 0:
                    print(f"{symbol}: rising by {change:.2f}")
                else:
                    print(f"{symbol}: falling by {-change:.2f}")
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
        prices[f"kama_{window}"] = talib.KAMA(prices[column], timeperiod=window)
        return prices

    def mesa_adaptive_moving_average(
        self,
        fast_limit: float = 0.5,
        slow_limit: float = 0.05,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the MESA adaptive moving average and its following average of one candle column.

        Args:
            fast_limit: The float upper limit of the adaptive smoothing factor.
            slow_limit: The float lower limit of the adaptive smoothing factor.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `mama` and `fama` columns added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's MESA adaptive moving average and its following line:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.mesa_adaptive_moving_average(days=365)
            print(candles[["datetime", "close", "mama", "fama"]].tail())
            ```

            Print the last day on which the NIFTY 50 index's MESA average crossed its following line:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            candles = nifty.mesa_adaptive_moving_average(days=365)
            last_cross = None
            mama = candles["mama"]
            fama = candles["fama"]
            for position in range(1, len(candles)):
                before = mama.iloc[position - 1] > fama.iloc[position - 1]
                after = mama.iloc[position] > fama.iloc[position]
                if before != after:
                    last_cross = candles["datetime"].iloc[position]
            print(last_cross)
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
        mama, fama = talib.MAMA(
            prices[column],
            fastlimit=fast_limit,
            slowlimit=slow_limit,
        )
        prices["mama"] = mama
        prices["fama"] = fama
        return prices

    def triangular_moving_average(
        self,
        window: int = 10,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the triangular moving average of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `trima_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's close and its twenty-day triangular moving average:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.triangular_moving_average(window=20, days=120)
            print(candles[["datetime", "close", "trima_20"]].tail())
            ```

            Print how far three shares closed from their triangular average, in percent:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "RELIANCE",
                "INFY",
                "HDFCBANK",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                last_row = share.triangular_moving_average(days=90).iloc[-1]
                distance = (last_row["close"] / last_row["trima_10"] - 1) * 100
                print(f"{symbol}: {distance:.2f}%")
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
        prices[f"trima_{window}"] = talib.TRIMA(prices[column], timeperiod=window)
        return prices

    def parabolic_sar(
        self,
        acceleration: float = 0.02,
        maximum: float = 0.2,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the parabolic stop and reverse from the high and low columns.

        Args:
            acceleration: The float acceleration factor added at each new extreme.
            maximum: The float largest acceleration factor allowed.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `psar` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's close and its parabolic stop and reverse for the last five days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.parabolic_sar(days=120)
            print(candles[["datetime", "close", "psar"]].tail())
            ```

            Say whether the parabolic stop puts each bank in an uptrend or a downtrend:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                last_row = share.parabolic_sar(days=120).iloc[-1]
                if last_row["close"] > last_row["psar"]:
                    print(f"{symbol}: uptrend, stop {last_row['psar']:.2f}")
                else:
                    print(f"{symbol}: downtrend, stop {last_row['psar']:.2f}")
            ```

            Print the NIFTY 50 index's parabolic stop with a slower acceleration:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            candles = nifty.parabolic_sar(
                acceleration=0.01,
                maximum=0.1,
                days=180,
            )
            print(candles[["datetime", "close", "psar"]].tail())
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
        prices["psar"] = talib.SAR(
            prices["high"],
            prices["low"],
            acceleration=acceleration,
            maximum=maximum,
        )
        return prices

    def mid_point(
        self,
        window: int = 10,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the midpoint of the highest and lowest value of one candle column over each window.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `mid_point_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the midpoint of Infosys's highest and lowest close over each ten days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.mid_point(days=60)
            print(candles[["datetime", "close", "mid_point_10"]].tail())
            ```

            Print whether the NIFTY 50 index closed above the midpoint of its last twenty closes:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            last_row = nifty.mid_point(window=20, days=90).iloc[-1]
            if last_row["close"] > last_row["mid_point_20"]:
                print("In the upper half of the recent range")
            else:
                print("In the lower half of the recent range")
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
        prices[f"mid_point_{window}"] = talib.MIDPOINT(
            prices[column], timeperiod=window
        )
        return prices

    def middle_price(
        self,
        window: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the midpoint of the highest high and lowest low over each window.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `middle_price_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the midpoint of Infosys's highest high and lowest low over each ten days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.middle_price(days=60)
            print(candles[["datetime", "close", "middle_price_10"]].tail())
            ```

            Print the twenty-day middle price of three IT shares, the base line of the Ichimoku cloud's kind:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                last_row = share.middle_price(window=20, days=90).iloc[-1]
                middle = last_row["middle_price_20"]
                print(f"{symbol}: close {last_row['close']}, middle {middle}")
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
        prices[f"middle_price_{window}"] = talib.MIDPRICE(
            prices["high"],
            prices["low"],
            timeperiod=window,
        )
        return prices
