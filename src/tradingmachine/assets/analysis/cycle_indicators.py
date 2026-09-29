"""Cycle indicators: the Hilbert transform family, which looks for repeating cycles in prices.

Each method fetches the instrument's candles through `prices`, adds one or more TA-Lib columns and returns the candles. The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.hilbert_transform_sine_wave(days=365)
"""

import datetime

import pandas as pd
import talib

from tradingmachine.assets.analysis import price_analysis


class CycleIndicators(price_analysis.PriceAnalysis):
    """Hilbert transform cycle indicators an instrument calculates from its candles."""

    def hilbert_transform_dominant_cycle_period(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Hilbert transform dominant cycle period of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `ht_dcperiod` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the length in days of the cycle the Hilbert transform finds in Infosys's close:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.hilbert_transform_dominant_cycle_period(days=365)
            print(candles[["datetime", "close", "ht_dcperiod"]].tail())
            ```

            Print the dominant cycle length of the NIFTY 50 index and of three banks:

            ```python
            from tradingmachine.assets import equities

            instruments = [
                equities.EquityIndex(exchange="nse", symbol="NIFTY"),
                equities.Equity(exchange="nse", symbol="HDFCBANK"),
                equities.Equity(exchange="nse", symbol="ICICIBANK"),
                equities.Equity(exchange="nse", symbol="SBIN"),
            ]
            for instrument in instruments:
                candles = instrument.hilbert_transform_dominant_cycle_period(
                    days=365,
                )
                period = candles["ht_dcperiod"].iloc[-1]
                print(f"{instrument.symbol}: {period:.1f} days")
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
        prices["ht_dcperiod"] = talib.HT_DCPERIOD(prices[column])
        return prices

    def hilbert_transform_dominant_cycle_phase(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Hilbert transform dominant cycle phase of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `ht_dcphase` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the phase, in degrees, of Infosys's dominant cycle for the last five days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.hilbert_transform_dominant_cycle_phase(days=365)
            print(candles[["datetime", "close", "ht_dcphase"]].tail())
            ```

            Print how far through its cycle the NIFTY 50 index's high is today:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            candles = nifty.hilbert_transform_dominant_cycle_phase(
                column="high",
                days=365,
            )
            phase = candles["ht_dcphase"].iloc[-1]
            print(f"{phase:.0f} degrees")
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
        prices["ht_dcphase"] = talib.HT_DCPHASE(prices[column])
        return prices

    def hilbert_transform_phasor_components(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Hilbert transform in-phase and quadrature phasor components of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `inphase` and `quadrature` columns added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the in-phase and quadrature components of Infosys's close:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.hilbert_transform_phasor_components(days=365)
            columns = [
                "datetime",
                "close",
                "inphase",
                "quadrature",
            ]
            print(candles[columns].tail())
            ```

            Work out the phase angle of the NIFTY 50 index's cycle from its two components:

            ```python
            import math

            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            candles = nifty.hilbert_transform_phasor_components(days=365)
            last_row = candles.iloc[-1]
            radians = math.atan2(last_row["quadrature"], last_row["inphase"])
            print(f"{math.degrees(radians):.0f} degrees")
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
        first, second = talib.HT_PHASOR(prices[column])
        prices["inphase"] = first
        prices["quadrature"] = second
        return prices

    def hilbert_transform_sine_wave(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Hilbert transform sine wave and lead sine wave of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `sine` and `lead_sine` columns added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the sine wave and lead sine wave of Infosys's close:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.hilbert_transform_sine_wave(days=365)
            print(candles[["datetime", "close", "sine", "lead_sine"]].tail())
            ```

            Say whether the lead sine is above the sine for three IT shares, which cycle traders read as a turn upwards:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "WIPRO",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                last_row = share.hilbert_transform_sine_wave(days=365).iloc[-1]
                if last_row["lead_sine"] > last_row["sine"]:
                    print(f"{symbol}: lead sine above, cycle turning up")
                else:
                    print(f"{symbol}: lead sine below, cycle turning down")
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
        first, second = talib.HT_SINE(prices[column])
        prices["sine"] = first
        prices["lead_sine"] = second
        return prices

    def hilbert_transform_trend_mode(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Hilbert transform trend mode of one candle column, 1 in a trend and 0 in a cycle.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `ht_trendmode` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print whether Infosys has been trending or cycling over the last five days:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.hilbert_transform_trend_mode(days=365)
            print(candles[["datetime", "close", "ht_trendmode"]].tail())
            ```

            Count the days in the last year the NIFTY 50 index spent trending:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            candles = nifty.hilbert_transform_trend_mode(days=365)
            trending_days = int(candles["ht_trendmode"].sum())
            print(f"{trending_days} of {len(candles)} days trending")
            ```

            Print whether an equal-weighted basket of three IT shares is trending today:

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
            candles = information_technology.hilbert_transform_trend_mode(
                days=365,
            )
            if candles["ht_trendmode"].iloc[-1] == 1:
                print("Trending")
            else:
                print("Cycling")
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
        prices["ht_trendmode"] = talib.HT_TRENDMODE(prices[column])
        return prices

    def hilbert_transform_trend_line(
        self,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Hilbert transform instantaneous trend line of one candle column.

        Args:
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `ht_trendline` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's close beside its Hilbert transform trend line:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            candles = infosys.hilbert_transform_trend_line(days=365)
            print(candles[["datetime", "close", "ht_trendline"]].tail())
            ```

            Print how far three banks closed from their instantaneous trend line, in percent:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "HDFCBANK",
                "ICICIBANK",
                "SBIN",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                last_row = share.hilbert_transform_trend_line(days=365).iloc[-1]
                ratio = last_row["close"] / last_row["ht_trendline"]
                distance = (ratio - 1) * 100
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
        prices["ht_trendline"] = talib.HT_TRENDLINE(prices[column])
        return prices
