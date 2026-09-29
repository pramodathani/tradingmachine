"""Momentum indicators: oscillators and directional measures of how fast prices move.

Each method fetches the instrument's candles through `prices`, adds one or more TA-Lib columns and returns the candles. The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.relative_strength_index(window=14, days=365)
"""

import datetime

import pandas as pd
import talib

from tradingmachine.assets.analysis import price_analysis


class MomentumIndicators(price_analysis.PriceAnalysis):
    """Oscillators and directional indicators an instrument calculates from its candles."""

    def moving_average_convergence_divergence(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the moving average convergence divergence line, its signal line and their difference.

        Args:
            fast_period: The int number of candles in the fast moving average.
            slow_period: The int number of candles in the slow moving average.
            signal_period: The int number of candles in the signal line's moving average.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `macd_<fast>_<slow>_<signal>` columns, with `_signal` and `_hist` variants added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five days of Infosys's MACD line, signal line and histogram:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.moving_average_convergence_divergence(days=180)
            columns = [
                "datetime",
                "macd_12_26_9",
                "macd_12_26_9_signal",
                "macd_12_26_9_hist",
            ]
            print(frame[columns].tail())
            ```

            List the days on which a faster NIFTY MACD crossed above its signal line:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.moving_average_convergence_divergence(
                fast_period=8,
                slow_period=21,
                signal_period=5,
                days=365,
            )
            histogram = frame["macd_8_21_5_hist"]
            crossed_above = (histogram > 0) & (histogram.shift(1) <= 0)
            print(frame["datetime"][crossed_above].dt.date.tolist())
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
        label = f"macd_{fast_period}_{slow_period}_{signal_period}"
        macd, signal, histogram = talib.MACD(
            prices[column],
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period,
        )
        prices[label] = macd
        prices[f"{label}_signal"] = signal
        prices[f"{label}_hist"] = histogram
        return prices

    def average_directional_movement_index(
        self,
        window: int = 14,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the average directional movement index.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `adx_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day average directional movement index:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.average_directional_movement_index(days=180)
            print(frame.set_index("datetime")["adx_14"].tail())
            ```

            Say whether NIFTY is trending or moving sideways, using the common threshold of 25:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.average_directional_movement_index(
                window=14,
                days=180,
            )
            latest = frame["adx_14"].iloc[-1]
            if latest > 25:
                print(f"NIFTY is trending, ADX {latest:.1f}")
            else:
                print(f"NIFTY is moving sideways, ADX {latest:.1f}")
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
        prices[f"adx_{window}"] = talib.ADX(
            prices["high"],
            prices["low"],
            prices["close"],
            timeperiod=window,
        )
        return prices

    def momentum(
        self,
        window: int = 14,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the momentum of one candle column, its change over each window.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `momentum_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Reliance's 10-day momentum of the close:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            frame = reliance.momentum(window=10, days=120)
            print(frame.set_index("datetime")["momentum_10"].tail())
            ```

            Compare the 20-day momentum of the daily high across four shares:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
                "RELIANCE",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                frame = share.momentum(window=20, column="high", days=120)
                print(symbol, round(frame["momentum_20"].iloc[-1], 2))
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
        prices[f"momentum_{window}"] = talib.MOM(prices[column], timeperiod=window)
        return prices

    def commodity_channel_index(
        self,
        window: int = 14,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the commodity channel index.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `cci_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 20-day commodity channel index:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.commodity_channel_index(window=20, days=180)
            print(frame.set_index("datetime")["cci_20"].tail())
            ```

            Count the days in the last year on which NIFTY's index was above 100 or below -100:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.commodity_channel_index(window=20, days=365)
            above = (frame["cci_20"] > 100).sum()
            below = (frame["cci_20"] < -100).sum()
            print(f"Above 100 on {above} days, below -100 on {below} days")
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
        prices[f"cci_{window}"] = talib.CCI(
            prices["high"],
            prices["low"],
            prices["close"],
            timeperiod=window,
        )
        return prices

    def average_directional_movement_index_rating(
        self,
        window: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the average directional movement index rating.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `adxr_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of HDFC Bank's 14-day rating:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            frame = hdfc_bank.average_directional_movement_index_rating(
                window=14,
                days=180,
            )
            print(frame.set_index("datetime")["adxr_14"].tail())
            ```

            Compare Infosys's latest rating with its latest average directional movement index:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            rating_frame = infosys.average_directional_movement_index_rating(
                window=14,
                days=180,
            )
            index_frame = infosys.average_directional_movement_index(
                window=14,
                days=180,
            )
            print("ADXR", round(rating_frame["adxr_14"].iloc[-1], 2))
            print("ADX", round(index_frame["adx_14"].iloc[-1], 2))
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
        prices[f"adxr_{window}"] = talib.ADXR(
            prices["high"],
            prices["low"],
            prices["close"],
            timeperiod=window,
        )
        return prices

    def absolute_price_oscillator(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        moving_average_type: int = 0,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the absolute price oscillator, the difference between a fast and a slow moving average.

        Args:
            fast_period: The int number of candles in the fast moving average.
            slow_period: The int number of candles in the slow moving average.
            moving_average_type: The int TA-Lib moving average type, where 0 is a simple moving average.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with an `apo_<fast>_<slow>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's absolute price oscillator:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.absolute_price_oscillator(days=180)
            print(frame.set_index("datetime")["apo_12_26"].tail())
            ```

            Say whether NIFTY's 5-day exponential average is above its 20-day one:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.absolute_price_oscillator(
                fast_period=5,
                slow_period=20,
                moving_average_type=1,
                days=120,
            )
            gap = round(frame["apo_5_20"].iloc[-1], 2)
            if gap > 0:
                print(f"The fast average is {gap} points above the slow one")
            else:
                print(f"The fast average is {-gap} points below the slow one")
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
        prices[f"apo_{fast_period}_{slow_period}"] = talib.APO(
            prices[column],
            fastperiod=fast_period,
            slowperiod=slow_period,
            matype=moving_average_type,
        )
        return prices

    def aroon(
        self,
        window: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Aroon down and Aroon up lines.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `aroon_down_<window>` and `aroon_up_<window>` columns added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five days of Infosys's 25-day Aroon down and Aroon up lines:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.aroon(window=25, days=180)
            columns = [
                "datetime",
                "aroon_down_25",
                "aroon_up_25",
            ]
            print(frame[columns].tail())
            ```

            Say whether new highs or new lows have been more recent on NIFTY:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.aroon(window=25, days=180)
            aroon_up = int(frame["aroon_up_25"].iloc[-1])
            aroon_down = int(frame["aroon_down_25"].iloc[-1])
            if aroon_up > aroon_down:
                print(f"New highs lead: up {aroon_up}, down {aroon_down}")
            else:
                print(f"New lows lead: up {aroon_up}, down {aroon_down}")
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
        aroon_down, aroon_up = talib.AROON(
            prices["high"],
            prices["low"],
            timeperiod=window,
        )
        prices[f"aroon_down_{window}"] = aroon_down
        prices[f"aroon_up_{window}"] = aroon_up
        return prices

    def aroon_oscillator(
        self,
        window: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Aroon oscillator, Aroon up minus Aroon down.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `aroon_osc_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of TCS's 14-day Aroon oscillator:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            frame = tcs.aroon_oscillator(window=14, days=180)
            print(frame.set_index("datetime")["aroon_osc_14"].tail())
            ```

            Count how many of NIFTY's last 60 days had a positive Aroon oscillator:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.aroon_oscillator(window=14, days=180)
            last_sixty = frame["aroon_osc_14"].tail(60)
            positive_days = (last_sixty > 0).sum()
            print(f"Positive on {positive_days} of {len(last_sixty)} days")
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
        prices[f"aroon_osc_{window}"] = talib.AROONOSC(
            prices["high"],
            prices["low"],
            timeperiod=window,
        )
        return prices

    def balance_of_power(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the balance of power.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `bop` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's balance of power:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.balance_of_power(days=60)
            print(frame.set_index("datetime")["bop"].tail())
            ```

            Smooth Reliance's balance of power over ten days to see who has been in control:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            frame = reliance.balance_of_power(days=120)
            smoothed = frame["bop"].rolling(10).mean().iloc[-1]
            if smoothed > 0:
                print(f"Buyers have been in control: {smoothed:.3f}")
            else:
                print(f"Sellers have been in control: {smoothed:.3f}")
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
        prices["bop"] = talib.BOP(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def chande_momentum_oscillator(
        self,
        window: int = 10,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the Chande momentum oscillator of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `cmo_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day Chande momentum oscillator:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.chande_momentum_oscillator(window=14, days=120)
            print(frame.set_index("datetime")["cmo_14"].tail())
            ```

            Label NIFTY as overbought above 50, oversold below -50, or neutral:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.chande_momentum_oscillator(window=14, days=120)
            latest = frame["cmo_14"].iloc[-1]
            if latest > 50:
                label = "overbought"
            elif latest < -50:
                label = "oversold"
            else:
                label = "neutral"
            print(f"NIFTY CMO {latest:.1f}: {label}")
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
        prices[f"cmo_{window}"] = talib.CMO(prices[column], timeperiod=window)
        return prices

    def directional_movement_index(
        self,
        window: int = 10,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the directional movement index.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `dx_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day directional movement index:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.directional_movement_index(window=14, days=120)
            print(frame.set_index("datetime")["dx_14"].tail())
            ```

            Average BANKNIFTY's directional movement index over the first quarter of 2026:

            ```python
            from tradingmachine.assets import equities

            bank_nifty = equities.EquityIndex(
                exchange="nse",
                symbol="BANKNIFTY",
            )
            frame = bank_nifty.directional_movement_index(
                window=14,
                from_date="2026-01-01",
                to_date="2026-03-31",
            )
            print(f"Average DX: {frame['dx_14'].mean():.2f}")
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
        prices[f"dx_{window}"] = talib.DX(
            prices["high"],
            prices["low"],
            prices["close"],
            timeperiod=window,
        )
        return prices

    def moving_average_convergence_divergence_extended(
        self,
        fast_period: int = 12,
        fast_moving_average_type: int = 0,
        slow_period: int = 26,
        slow_moving_average_type: int = 0,
        signal_period: int = 9,
        signal_moving_average_type: int = 0,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the moving average convergence divergence with a chosen moving average type for each of its three averages.

        Args:
            fast_period: The int number of candles in the fast moving average.
            fast_moving_average_type: The int TA-Lib moving average type of the fast average, where 0 is a simple moving average.
            slow_period: The int number of candles in the slow moving average.
            slow_moving_average_type: The int TA-Lib moving average type of the slow average, where 0 is a simple moving average.
            signal_period: The int number of candles in the signal line's moving average.
            signal_moving_average_type: The int TA-Lib moving average type of the signal line, where 0 is a simple moving average.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `macd_<fast>_<slow>_<signal>`, `macd_signal_...` and `macd_hist_...` columns added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print Infosys's MACD built from exponential averages throughout:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.moving_average_convergence_divergence_extended(
                fast_moving_average_type=1,
                slow_moving_average_type=1,
                signal_moving_average_type=1,
                days=180,
            )
            columns = [
                "datetime",
                "macd_12_26_9",
                "macd_signal_12_26_9",
                "macd_hist_12_26_9",
            ]
            print(frame[columns].tail())
            ```

            Print NIFTY's latest histogram from weighted fast and slow averages and a simple signal line:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.moving_average_convergence_divergence_extended(
                fast_period=10,
                fast_moving_average_type=2,
                slow_period=30,
                slow_moving_average_type=2,
                signal_period=7,
                signal_moving_average_type=0,
                days=240,
            )
            print(round(frame["macd_hist_10_30_7"].iloc[-1], 2))
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
        suffix = f"{fast_period}_{slow_period}_{signal_period}"
        macd, signal, histogram = talib.MACDEXT(
            prices[column],
            fastperiod=fast_period,
            fastmatype=fast_moving_average_type,
            slowperiod=slow_period,
            slowmatype=slow_moving_average_type,
            signalperiod=signal_period,
            signalmatype=signal_moving_average_type,
        )
        prices[f"macd_{suffix}"] = macd
        prices[f"macd_signal_{suffix}"] = signal
        prices[f"macd_hist_{suffix}"] = histogram
        return prices

    def money_flow_index(
        self,
        window: int = 14,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the money flow index, a relative strength index weighted by volume.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with an `mfi_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day money flow index:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.money_flow_index(window=14, days=120)
            print(frame.set_index("datetime")["mfi_14"].tail())
            ```

            Label each of four shares as overbought above 80, oversold below 20, or neutral:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
                "RELIANCE",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                frame = share.money_flow_index(window=14, days=120)
                latest = frame["mfi_14"].iloc[-1]
                if latest > 80:
                    label = "overbought"
                elif latest < 20:
                    label = "oversold"
                else:
                    label = "neutral"
                print(f"{symbol}: {latest:.1f} {label}")
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
        prices[f"mfi_{window}"] = talib.MFI(
            prices["high"],
            prices["low"],
            prices["close"],
            prices["volume"],
            timeperiod=window,
        )
        return prices

    def minus_directional_indicator(
        self,
        window: int = 14,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the minus directional indicator.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `minus_di_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day minus directional indicator:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.minus_directional_indicator(window=14, days=120)
            print(frame.set_index("datetime")["minus_di_14"].tail())
            ```

            Say whether sellers or buyers dominate NIFTY by comparing the minus and plus indicators:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            minus_frame = nifty.minus_directional_indicator(window=14, days=120)
            plus_frame = nifty.plus_directional_indicator(window=14, days=120)
            minus_value = round(minus_frame["minus_di_14"].iloc[-1], 1)
            plus_value = round(plus_frame["plus_di_14"].iloc[-1], 1)
            if minus_value > plus_value:
                print(f"Sellers dominate: -DI {minus_value}, +DI {plus_value}")
            else:
                print(f"Buyers dominate: -DI {minus_value}, +DI {plus_value}")
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
        prices[f"minus_di_{window}"] = talib.MINUS_DI(
            prices["high"],
            prices["low"],
            prices["close"],
            timeperiod=window,
        )
        return prices

    def minus_directional_movement(
        self,
        window: int = 14,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the minus directional movement.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `minus_dm_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of TCS's 14-day minus directional movement:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            frame = tcs.minus_directional_movement(window=14, days=120)
            print(frame.set_index("datetime")["minus_dm_14"].tail())
            ```

            Find the day on which NIFTY's 7-day minus directional movement peaked this year:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.minus_directional_movement(
                window=7,
                from_date="2026-01-01",
                to_date="2026-09-28",
            )
            peak_row = frame["minus_dm_7"].idxmax()
            peak_day = frame.loc[peak_row, "datetime"].date()
            print(peak_day, round(frame.loc[peak_row, "minus_dm_7"], 2))
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
        prices[f"minus_dm_{window}"] = talib.MINUS_DM(
            prices["high"],
            prices["low"],
            timeperiod=window,
        )
        return prices

    def plus_directional_indicator(
        self,
        window: int = 14,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the plus directional indicator.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `plus_di_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day plus directional indicator:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.plus_directional_indicator(window=14, days=120)
            print(frame.set_index("datetime")["plus_di_14"].tail())
            ```

            Count the days in the last half year on which HDFC Bank's indicator was above 25:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            frame = hdfc_bank.plus_directional_indicator(window=14, days=180)
            print(f"Above 25 on {(frame['plus_di_14'] > 25).sum()} days")
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
        prices[f"plus_di_{window}"] = talib.PLUS_DI(
            prices["high"],
            prices["low"],
            prices["close"],
            timeperiod=window,
        )
        return prices

    def plus_directional_movement(
        self,
        window: int = 14,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the plus directional movement.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `plus_dm_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day plus directional movement:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.plus_directional_movement(window=14, days=120)
            print(frame.set_index("datetime")["plus_dm_14"].tail())
            ```

            Print NIFTY's latest 7-day plus directional movement in index points:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.plus_directional_movement(window=7, days=60)
            print(f"{frame['plus_dm_7'].iloc[-1]:.2f} points")
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
        prices[f"plus_dm_{window}"] = talib.PLUS_DM(
            prices["high"],
            prices["low"],
            timeperiod=window,
        )
        return prices

    def percentage_price_oscillator(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        moving_average_type: int = 0,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the percentage price oscillator, the gap between a fast and a slow moving average as a percentage.

        Args:
            fast_period: The int number of candles in the fast moving average.
            slow_period: The int number of candles in the slow moving average.
            moving_average_type: The int TA-Lib moving average type, where 0 is a simple moving average.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `ppo<fast>_<slow>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's percentage price oscillator:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.percentage_price_oscillator(days=180)
            print(frame.set_index("datetime")["ppo12_26"].tail())
            ```

            Compare four shares by the percentage gap between their exponential averages:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
                "RELIANCE",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                frame = share.percentage_price_oscillator(
                    moving_average_type=1,
                    days=180,
                )
                print(f"{symbol}: {frame['ppo12_26'].iloc[-1]:.2f}%")
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
        prices[f"ppo{fast_period}_{slow_period}"] = talib.PPO(
            prices[column],
            fastperiod=fast_period,
            slowperiod=slow_period,
            matype=moving_average_type,
        )
        return prices

    def rate_of_change(
        self,
        window: int = 14,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the rate of change of one candle column as a percentage.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `roc_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day rate of change in percent:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.rate_of_change(window=14, days=120)
            print(frame.set_index("datetime")["roc_14"].tail())
            ```

            Find NIFTY's best and worst 20-day stretch in the first half of 2026:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.rate_of_change(
                window=20,
                from_date="2026-01-01",
                to_date="2026-06-30",
            )
            print(f"Best 20 days: {frame['roc_20'].max():.2f}%")
            print(f"Worst 20 days: {frame['roc_20'].min():.2f}%")
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
        prices[f"roc_{window}"] = talib.ROC(prices[column], timeperiod=window)
        return prices

    def rate_of_change_percent(
        self,
        window: int = 14,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the rate of change of one candle column as a fraction.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `rocp_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day rate of change as a fraction:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.rate_of_change_percent(window=14, days=120)
            print(frame.set_index("datetime")["rocp_14"].tail())
            ```

            Print how far TCS's daily high has moved over the last five days, as a fraction:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            frame = tcs.rate_of_change_percent(window=5, column="high", days=60)
            print(round(frame["rocp_5"].iloc[-1], 4))
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
        prices[f"rocp_{window}"] = talib.ROCP(prices[column], timeperiod=window)
        return prices

    def rate_of_change_ratio(
        self,
        window: int = 14,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the rate of change of one candle column as a ratio.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `rocr_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day rate of change as a ratio:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.rate_of_change_ratio(window=14, days=120)
            print(frame.set_index("datetime")["rocr_14"].tail())
            ```

            Say whether NIFTY is higher or lower than ten days ago:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.rate_of_change_ratio(window=10, days=60)
            ratio = frame["rocr_10"].iloc[-1]
            if ratio > 1:
                print(f"Higher than ten days ago, ratio {ratio:.4f}")
            else:
                print(f"Lower than ten days ago, ratio {ratio:.4f}")
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
        prices[f"rocr_{window}"] = talib.ROCR(prices[column], timeperiod=window)
        return prices

    def relative_strength_index(
        self,
        window: int = 14,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the relative strength index of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `rsi_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day relative strength index:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.relative_strength_index(window=14, days=120)
            print(frame.set_index("datetime")["rsi_14"].tail())
            ```

            Label each of four shares as overbought above 70, oversold below 30, or neutral:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
                "RELIANCE",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                frame = share.relative_strength_index(window=14, days=120)
                latest = frame["rsi_14"].iloc[-1]
                if latest > 70:
                    label = "overbought"
                elif latest < 30:
                    label = "oversold"
                else:
                    label = "neutral"
                print(f"{symbol}: {latest:.1f} {label}")
            ```

            Print NIFTY's 9-day relative strength index of the daily high for a fixed quarter:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.relative_strength_index(
                window=9,
                column="high",
                from_date="2026-04-01",
                to_date="2026-06-30",
            )
            print(frame.set_index("datetime")["rsi_9"].dropna().round(1))
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
        prices[f"rsi_{window}"] = talib.RSI(prices[column], timeperiod=window)
        return prices

    def stochastic_oscillator(
        self,
        fast_k_period: int = 5,
        slow_k_period: int = 3,
        slow_k_moving_average_type: int = 0,
        slow_d_period: int = 3,
        slow_d_moving_average_type: int = 0,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the slow stochastic oscillator's %K and %D lines.

        Args:
            fast_k_period: The int number of candles in the fast %K calculation.
            slow_k_period: The int number of candles smoothing fast %K into slow %K.
            slow_k_moving_average_type: The int TA-Lib moving average type for slow %K, where 0 is a simple moving average.
            slow_d_period: The int number of candles smoothing slow %K into slow %D.
            slow_d_moving_average_type: The int TA-Lib moving average type for slow %D, where 0 is a simple moving average.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `slowk_<period>` and `slowd_<period>` columns added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five days of Infosys's slow %K and %D lines:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.stochastic_oscillator(days=90)
            columns = [
                "datetime",
                "slowk_3",
                "slowd_3",
            ]
            print(frame[columns].tail())
            ```

            Check whether NIFTY's 14-day slow %K has just crossed above %D:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.stochastic_oscillator(
                fast_k_period=14,
                slow_k_period=3,
                slow_d_period=3,
                days=120,
            )
            difference = frame["slowk_3"] - frame["slowd_3"]
            crossed = difference.iloc[-1] > 0 and difference.iloc[-2] <= 0
            print(f"%K {frame['slowk_3'].iloc[-1]:.1f}")
            print(f"Crossed above %D: {crossed}")
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
        slow_k, slow_d = talib.STOCH(
            prices["high"],
            prices["low"],
            prices["close"],
            fastk_period=fast_k_period,
            slowk_period=slow_k_period,
            slowk_matype=slow_k_moving_average_type,
            slowd_period=slow_d_period,
            slowd_matype=slow_d_moving_average_type,
        )
        prices[f"slowk_{slow_k_period}"] = slow_k
        prices[f"slowd_{slow_d_period}"] = slow_d
        return prices

    def stochastic_fast_oscillator(
        self,
        fast_k_period: int = 5,
        fast_d_period: int = 3,
        fast_d_moving_average_type: int = 0,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the fast stochastic oscillator's %K and %D lines.

        Args:
            fast_k_period: The int number of candles in the fast %K calculation.
            fast_d_period: The int number of candles smoothing fast %K into fast %D.
            fast_d_moving_average_type: The int TA-Lib moving average type for fast %D, where 0 is a simple moving average.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `stochf_fastk<period>` and `stochf_fastd<period>` columns added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five days of Infosys's fast %K and %D lines:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.stochastic_fast_oscillator(days=90)
            columns = [
                "datetime",
                "stochf_fastk5",
                "stochf_fastd3",
            ]
            print(frame[columns].tail())
            ```

            Print where NIFTY closed within its 14-day range, as fast %K:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.stochastic_fast_oscillator(
                fast_k_period=14,
                fast_d_period=3,
                days=90,
            )
            fast_k = round(frame["stochf_fastk14"].iloc[-1], 1)
            print(f"{fast_k}% of the 14-day range")
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
        fast_k, fast_d = talib.STOCHF(
            prices["high"],
            prices["low"],
            prices["close"],
            fastk_period=fast_k_period,
            fastd_period=fast_d_period,
            fastd_matype=fast_d_moving_average_type,
        )
        prices[f"stochf_fastk{fast_k_period}"] = fast_k
        prices[f"stochf_fastd{fast_d_period}"] = fast_d
        return prices

    def stochastic_relative_strength_index(
        self,
        window: int = 14,
        fast_k_period: int = 5,
        fast_d_period: int = 3,
        fast_d_moving_average_type: int = 0,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the stochastic relative strength index's %K and %D lines for one candle column.

        Args:
            window: The int number of candles in the relative strength index that the stochastic is taken of.
            fast_k_period: The int number of relative strength index values the stochastic %K looks back over.
            fast_d_period: The int number of candles smoothing %K into %D.
            fast_d_moving_average_type: The int TA-Lib moving average type for %D, where 0 is a simple moving average.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with `stochrsi_fastk<period>` and `stochrsi_fastd<period>` columns added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five days of Infosys's stochastic relative strength index:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.stochastic_relative_strength_index(days=120)
            columns = [
                "datetime",
                "stochrsi_fastk5",
                "stochrsi_fastd3",
            ]
            print(frame[columns].tail())
            ```

            Print NIFTY's latest 14-period stochastic relative strength index lines:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.stochastic_relative_strength_index(
                window=14,
                fast_k_period=14,
                fast_d_period=3,
                days=180,
            )
            print(f"%K {frame['stochrsi_fastk14'].iloc[-1]:.1f}")
            print(f"%D {frame['stochrsi_fastd3'].iloc[-1]:.1f}")
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
        fast_k, fast_d = talib.STOCHRSI(
            prices[column],
            timeperiod=window,
            fastk_period=fast_k_period,
            fastd_period=fast_d_period,
            fastd_matype=fast_d_moving_average_type,
        )
        prices[f"stochrsi_fastk{fast_k_period}"] = fast_k
        prices[f"stochrsi_fastd{fast_d_period}"] = fast_d
        return prices

    def trix(
        self,
        window: int = 15,
        column: str = "close",
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds TRIX, the rate of change of a triple smoothed exponential moving average of one candle column.

        Args:
            window: The int number of candles in each calculation window.
            column: The str name of the candle column to use, such as `close`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `trix_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 15-day TRIX:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.trix(days=180)
            print(frame.set_index("datetime")["trix_15"].tail())
            ```

            Say whether NIFTY's 9-day TRIX is rising or falling:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.trix(window=9, days=180)
            latest = frame["trix_9"].iloc[-1]
            previous = frame["trix_9"].iloc[-2]
            if latest > previous:
                print(f"TRIX is rising: {previous:.4f} to {latest:.4f}")
            else:
                print(f"TRIX is falling: {previous:.4f} to {latest:.4f}")
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
        prices[f"trix_{window}"] = talib.TRIX(prices[column], timeperiod=window)
        return prices

    def ultimate_oscillator(
        self,
        fast_period: int = 7,
        slow_period: int = 14,
        signal_period: int = 28,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds the ultimate oscillator, which blends buying pressure over three windows.

        Args:
            fast_period: The int number of candles in the shortest window.
            slow_period: The int number of candles in the middle window.
            signal_period: The int number of candles in the longest window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with an `ultosc_<fast>_<slow>_<signal>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's ultimate oscillator:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.ultimate_oscillator(days=120)
            print(frame.set_index("datetime")["ultosc_7_14_28"].tail())
            ```

            Label Reliance as overbought above 70, oversold below 30, or neutral:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            frame = reliance.ultimate_oscillator(days=120)
            latest = frame["ultosc_7_14_28"].iloc[-1]
            if latest > 70:
                label = "overbought"
            elif latest < 30:
                label = "oversold"
            else:
                label = "neutral"
            print(f"Reliance ultimate oscillator {latest:.1f}: {label}")
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
        prices[f"ultosc_{fast_period}_{slow_period}_{signal_period}"] = talib.ULTOSC(
            prices["high"],
            prices["low"],
            prices["close"],
            timeperiod1=fast_period,
            timeperiod2=slow_period,
            timeperiod3=signal_period,
        )
        return prices

    def williams_percent_r(
        self,
        window: int = 14,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Adds Williams %R.

        Args:
            window: The int number of candles in each calculation window.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `willr_<window>` column added, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the last five values of Infosys's 14-day Williams %R:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            frame = infosys.williams_percent_r(window=14, days=90)
            print(frame.set_index("datetime")["willr_14"].tail())
            ```

            Count the days in the last year on which NIFTY's Williams %R was below -80:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            frame = nifty.williams_percent_r(window=14, days=365)
            print(f"Below -80 on {(frame['willr_14'] < -80).sum()} days")
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
        prices[f"willr_{window}"] = talib.WILLR(
            prices["high"],
            prices["low"],
            prices["close"],
            timeperiod=window,
        )
        return prices
