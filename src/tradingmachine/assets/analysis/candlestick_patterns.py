"""Candlestick patterns: TA-Lib's recognisers for named one to five candle formations.

Each method fetches the instrument's candles through `prices`, adds one or more TA-Lib columns and returns the candles. The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.candle_hammer(days=365)
"""

import datetime

import pandas as pd
import talib

from tradingmachine.assets.analysis import price_analysis


class CandlestickPatterns(price_analysis.PriceAnalysis):
    """Candlestick pattern recognisers an instrument runs over its candles."""

    def candle_two_crows(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the two crows candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_two_crows` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the dates in the last year when the two crows pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_two_crows(days=365)
            pattern_column = "candle_two_crows"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
            ```

            Compare how often the two crows pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_two_crows"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_two_crows(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
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
        prices["candle_two_crows"] = talib.CDL2CROWS(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_three_black_crows(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the three black crows candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_three_black_crows` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the bullish and the bearish three black crows signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_three_black_crows(days=730)
            pattern_column = "candle_three_black_crows"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
            ```

            Count the three black crows matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_three_black_crows(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_three_black_crows"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
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
        prices["candle_three_black_crows"] = talib.CDL3BLACKCROWS(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_three_inside_up_down(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the three inside up or down candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_three_inside_up_down` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Find the most recent three inside up or down pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_three_inside_up_down(days=1095)
            pattern_column = "candle_three_inside_up_down"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
            ```

            Measure the average return on the day after a three inside up or down pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_three_inside_up_down(days=1825)
            pattern_column = "candle_three_inside_up_down"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
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
        prices["candle_three_inside_up_down"] = talib.CDL3INSIDE(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_three_line_strike(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the three line strike candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_three_line_strike` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Compare how often the three line strike pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_three_line_strike"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_three_line_strike(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
            ```

            Check whether the latest Nifty candle is a three line strike pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_three_line_strike(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_three_line_strike"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
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
        prices["candle_three_line_strike"] = talib.CDL3LINESTRIKE(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_three_outside_up_down(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the three outside up or down candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_three_outside_up_down` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the three outside up or down matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_three_outside_up_down(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_three_outside_up_down"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
            ```

            Print the unadjusted candles of State Bank of India that formed a three outside up or down pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_three_outside_up_down(
                days=180,
                adjusted=False,
            )
            pattern_column = "candle_three_outside_up_down"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
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
        prices["candle_three_outside_up_down"] = talib.CDL3OUTSIDE(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_three_stars_in_the_south(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the three stars in the south candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_three_stars_in_the_south` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Measure the average return on the day after a three stars in the south pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_three_stars_in_the_south(days=1825)
            pattern_column = "candle_three_stars_in_the_south"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
            ```

            Print the dates in the last year when the three stars in the south pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_three_stars_in_the_south(days=365)
            pattern_column = "candle_three_stars_in_the_south"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
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
        prices["candle_three_stars_in_the_south"] = talib.CDL3STARSINSOUTH(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_three_white_soldiers(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the three white soldiers candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_three_white_soldiers` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Check whether the latest Nifty candle is a three white soldiers pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_three_white_soldiers(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_three_white_soldiers"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
            ```

            Count the bullish and the bearish three white soldiers signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_three_white_soldiers(days=730)
            pattern_column = "candle_three_white_soldiers"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
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
        prices["candle_three_white_soldiers"] = talib.CDL3WHITESOLDIERS(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_abandoned_baby(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the abandoned baby candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_abandoned_baby` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the unadjusted candles of State Bank of India that formed a abandoned baby pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_abandoned_baby(
                days=180,
                adjusted=False,
            )
            pattern_column = "candle_abandoned_baby"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
            ```

            Find the most recent abandoned baby pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_abandoned_baby(days=1095)
            pattern_column = "candle_abandoned_baby"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
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
        prices["candle_abandoned_baby"] = talib.CDLABANDONEDBABY(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_advance_block(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the advance block candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_advance_block` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the dates in the last year when the advance block pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_advance_block(days=365)
            pattern_column = "candle_advance_block"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
            ```

            Compare how often the advance block pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_advance_block"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_advance_block(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
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
        prices["candle_advance_block"] = talib.CDLADVANCEBLOCK(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_belt_hold(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the belt hold candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_belt_hold` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the bullish and the bearish belt hold signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_belt_hold(days=730)
            pattern_column = "candle_belt_hold"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
            ```

            Count the belt hold matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_belt_hold(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_belt_hold"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
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
        prices["candle_belt_hold"] = talib.CDLBELTHOLD(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_breakaway(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the breakaway candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_breakaway` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Find the most recent breakaway pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_breakaway(days=1095)
            pattern_column = "candle_breakaway"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
            ```

            Measure the average return on the day after a breakaway pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_breakaway(days=1825)
            pattern_column = "candle_breakaway"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
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
        prices["candle_breakaway"] = talib.CDLBREAKAWAY(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_closing_marubozu(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the closing marubozu candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_closing_marubozu` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Compare how often the closing marubozu pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_closing_marubozu"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_closing_marubozu(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
            ```

            Check whether the latest Nifty candle is a closing marubozu pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_closing_marubozu(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_closing_marubozu"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
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
        prices["candle_closing_marubozu"] = talib.CDLCLOSINGMARUBOZU(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_concealing_baby_swallow(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the concealing baby swallow candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_concealing_baby_swallow` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the concealing baby swallow matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_concealing_baby_swallow(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_concealing_baby_swallow"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
            ```

            Print the unadjusted candles of State Bank of India that formed a concealing baby swallow pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_concealing_baby_swallow(
                days=180,
                adjusted=False,
            )
            pattern_column = "candle_concealing_baby_swallow"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
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
        prices["candle_concealing_baby_swallow"] = talib.CDLCONCEALBABYSWALL(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_counter_attack(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the counterattack candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_counter_attack` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Measure the average return on the day after a counterattack pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_counter_attack(days=1825)
            pattern_column = "candle_counter_attack"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
            ```

            Print the dates in the last year when the counterattack pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_counter_attack(days=365)
            pattern_column = "candle_counter_attack"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
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
        prices["candle_counter_attack"] = talib.CDLCOUNTERATTACK(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_dark_cloud_cover(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the dark cloud cover candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_dark_cloud_cover` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Check whether the latest Nifty candle is a dark cloud cover pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_dark_cloud_cover(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_dark_cloud_cover"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
            ```

            Count the bullish and the bearish dark cloud cover signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_dark_cloud_cover(days=730)
            pattern_column = "candle_dark_cloud_cover"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
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
        prices["candle_dark_cloud_cover"] = talib.CDLDARKCLOUDCOVER(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_doji(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the doji candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_doji` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the unadjusted candles of State Bank of India that formed a doji pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_doji(days=180, adjusted=False)
            pattern_column = "candle_doji"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
            ```

            Find the most recent doji pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_doji(days=1095)
            pattern_column = "candle_doji"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
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
        prices["candle_doji"] = talib.CDLDOJI(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_doji_star(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the doji star candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_doji_star` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the dates in the last year when the doji star pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_doji_star(days=365)
            pattern_column = "candle_doji_star"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
            ```

            Compare how often the doji star pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_doji_star"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_doji_star(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
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
        prices["candle_doji_star"] = talib.CDLDOJISTAR(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_dragonfly_doji(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the dragonfly doji candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_dragonfly_doji` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the bullish and the bearish dragonfly doji signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_dragonfly_doji(days=730)
            pattern_column = "candle_dragonfly_doji"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
            ```

            Count the dragonfly doji matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_dragonfly_doji(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_dragonfly_doji"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
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
        prices["candle_dragonfly_doji"] = talib.CDLDRAGONFLYDOJI(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_engulfing(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the engulfing candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_engulfing` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Find the most recent engulfing pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_engulfing(days=1095)
            pattern_column = "candle_engulfing"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
            ```

            Measure the average return on the day after a engulfing pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_engulfing(days=1825)
            pattern_column = "candle_engulfing"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
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
        prices["candle_engulfing"] = talib.CDLENGULFING(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_evening_doji_star(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the evening doji star candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_evening_dojistar` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Compare how often the evening doji star pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_evening_dojistar"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_evening_doji_star(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
            ```

            Check whether the latest Nifty candle is a evening doji star pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_evening_doji_star(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_evening_dojistar"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
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
        prices["candle_evening_dojistar"] = talib.CDLEVENINGDOJISTAR(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_evening_star(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the evening star candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_evening_star` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the evening star matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_evening_star(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_evening_star"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
            ```

            Print the unadjusted candles of State Bank of India that formed a evening star pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_evening_star(
                days=180,
                adjusted=False,
            )
            pattern_column = "candle_evening_star"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
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
        prices["candle_evening_star"] = talib.CDLEVENINGSTAR(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_side_by_side_white_lines(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the up or down gap side by side white lines candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_side_by_side_white_lines` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Measure the average return on the day after a up or down gap side by side white lines pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_side_by_side_white_lines(days=1825)
            pattern_column = "candle_side_by_side_white_lines"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
            ```

            Print the dates in the last year when the up or down gap side by side white lines pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_side_by_side_white_lines(days=365)
            pattern_column = "candle_side_by_side_white_lines"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
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
        prices["candle_side_by_side_white_lines"] = talib.CDLGAPSIDESIDEWHITE(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_gravestone_doji(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the gravestone doji candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_gravestone_doji` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Check whether the latest Nifty candle is a gravestone doji pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_gravestone_doji(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_gravestone_doji"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
            ```

            Count the bullish and the bearish gravestone doji signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_gravestone_doji(days=730)
            pattern_column = "candle_gravestone_doji"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
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
        prices["candle_gravestone_doji"] = talib.CDLGRAVESTONEDOJI(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_hammer(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the hammer candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_hammer` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the unadjusted candles of State Bank of India that formed a hammer pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_hammer(days=180, adjusted=False)
            pattern_column = "candle_hammer"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
            ```

            Find the most recent hammer pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_hammer(days=1095)
            pattern_column = "candle_hammer"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
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
        prices["candle_hammer"] = talib.CDLHAMMER(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_hanging_man(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the hanging man candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_hangingman` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the dates in the last year when the hanging man pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_hanging_man(days=365)
            pattern_column = "candle_hangingman"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
            ```

            Compare how often the hanging man pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_hangingman"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_hanging_man(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
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
        prices["candle_hangingman"] = talib.CDLHANGINGMAN(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_harami(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the harami candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_harami` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the bullish and the bearish harami signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_harami(days=730)
            pattern_column = "candle_harami"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
            ```

            Count the harami matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_harami(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_harami"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
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
        prices["candle_harami"] = talib.CDLHARAMI(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_harami_cross(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the harami cross candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_harami_cross` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Find the most recent harami cross pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_harami_cross(days=1095)
            pattern_column = "candle_harami_cross"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
            ```

            Measure the average return on the day after a harami cross pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_harami_cross(days=1825)
            pattern_column = "candle_harami_cross"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
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
        prices["candle_harami_cross"] = talib.CDLHARAMICROSS(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_high_wave(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the high wave candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_high_wave` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Compare how often the high wave pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_high_wave"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_high_wave(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
            ```

            Check whether the latest Nifty candle is a high wave pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_high_wave(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_high_wave"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
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
        prices["candle_high_wave"] = talib.CDLHIGHWAVE(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_hikkake(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the hikkake candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_hikkake` column added, which is 100 for a bullish match, -100 for a bearish match, 200 or -200 when the match is confirmed and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the hikkake matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_hikkake(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_hikkake"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
            ```

            Print the unadjusted candles of State Bank of India that formed a hikkake pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_hikkake(days=180, adjusted=False)
            pattern_column = "candle_hikkake"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
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
        prices["candle_hikkake"] = talib.CDLHIKKAKE(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_modified_hikkake(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the modified hikkake candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_modified_hikkake` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Measure the average return on the day after a modified hikkake pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_modified_hikkake(days=1825)
            pattern_column = "candle_modified_hikkake"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
            ```

            Print the dates in the last year when the modified hikkake pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_modified_hikkake(days=365)
            pattern_column = "candle_modified_hikkake"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
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
        prices["candle_modified_hikkake"] = talib.CDLHIKKAKEMOD(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_homing_pigeon(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the homing pigeon candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_homing_pigeon` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Check whether the latest Nifty candle is a homing pigeon pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_homing_pigeon(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_homing_pigeon"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
            ```

            Count the bullish and the bearish homing pigeon signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_homing_pigeon(days=730)
            pattern_column = "candle_homing_pigeon"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
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
        prices["candle_homing_pigeon"] = talib.CDLHOMINGPIGEON(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_identical_three_crows(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the identical three crows candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_identical_three_crows` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the unadjusted candles of State Bank of India that formed a identical three crows pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_identical_three_crows(
                days=180,
                adjusted=False,
            )
            pattern_column = "candle_identical_three_crows"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
            ```

            Find the most recent identical three crows pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_identical_three_crows(days=1095)
            pattern_column = "candle_identical_three_crows"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
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
        prices["candle_identical_three_crows"] = talib.CDLIDENTICAL3CROWS(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_in_neck(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the in-neck candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_in_neck` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the dates in the last year when the in-neck pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_in_neck(days=365)
            pattern_column = "candle_in_neck"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
            ```

            Compare how often the in-neck pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_in_neck"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_in_neck(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
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
        prices["candle_in_neck"] = talib.CDLINNECK(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_inverted_hammer(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the inverted hammer candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_inverted_hammer` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the bullish and the bearish inverted hammer signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_inverted_hammer(days=730)
            pattern_column = "candle_inverted_hammer"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
            ```

            Count the inverted hammer matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_inverted_hammer(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_inverted_hammer"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
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
        prices["candle_inverted_hammer"] = talib.CDLINVERTEDHAMMER(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_kicking(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the kicking candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_kicking` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Find the most recent kicking pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_kicking(days=1095)
            pattern_column = "candle_kicking"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
            ```

            Measure the average return on the day after a kicking pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_kicking(days=1825)
            pattern_column = "candle_kicking"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
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
        prices["candle_kicking"] = talib.CDLKICKING(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_kicking_by_length(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the kicking, bull or bear decided by the longer marubozu, candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_kicking_by_length` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Compare how often the kicking, bull or bear decided by the longer marubozu, pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_kicking_by_length"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_kicking_by_length(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
            ```

            Check whether the latest Nifty candle is a kicking, bull or bear decided by the longer marubozu, pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_kicking_by_length(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_kicking_by_length"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
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
        prices["candle_kicking_by_length"] = talib.CDLKICKINGBYLENGTH(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_ladder_bottom(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the ladder bottom candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_ladder_bottom` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the ladder bottom matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_ladder_bottom(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_ladder_bottom"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
            ```

            Print the unadjusted candles of State Bank of India that formed a ladder bottom pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_ladder_bottom(
                days=180,
                adjusted=False,
            )
            pattern_column = "candle_ladder_bottom"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
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
        prices["candle_ladder_bottom"] = talib.CDLLADDERBOTTOM(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_long_legged_doji(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the long legged doji candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_long_legged_doji` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Measure the average return on the day after a long legged doji pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_long_legged_doji(days=1825)
            pattern_column = "candle_long_legged_doji"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
            ```

            Print the dates in the last year when the long legged doji pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_long_legged_doji(days=365)
            pattern_column = "candle_long_legged_doji"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
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
        prices["candle_long_legged_doji"] = talib.CDLLONGLEGGEDDOJI(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_long_line(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the long line candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_long_line` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Check whether the latest Nifty candle is a long line pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_long_line(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_long_line"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
            ```

            Count the bullish and the bearish long line signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_long_line(days=730)
            pattern_column = "candle_long_line"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
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
        prices["candle_long_line"] = talib.CDLLONGLINE(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_marubozu(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the marubozu candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_marubozu` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the unadjusted candles of State Bank of India that formed a marubozu pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_marubozu(days=180, adjusted=False)
            pattern_column = "candle_marubozu"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
            ```

            Find the most recent marubozu pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_marubozu(days=1095)
            pattern_column = "candle_marubozu"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
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
        prices["candle_marubozu"] = talib.CDLMARUBOZU(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_matching_low(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the matching low candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_matching_low` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the dates in the last year when the matching low pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_matching_low(days=365)
            pattern_column = "candle_matching_low"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
            ```

            Compare how often the matching low pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_matching_low"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_matching_low(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
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
        prices["candle_matching_low"] = talib.CDLMATCHINGLOW(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_mat_hold(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the mat hold candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_mat_hold` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the bullish and the bearish mat hold signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_mat_hold(days=730)
            pattern_column = "candle_mat_hold"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
            ```

            Count the mat hold matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_mat_hold(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_mat_hold"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
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
        prices["candle_mat_hold"] = talib.CDLMATHOLD(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_morning_star(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the morning star candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_morning_star` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Find the most recent morning star pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_morning_star(days=1095)
            pattern_column = "candle_morning_star"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
            ```

            Measure the average return on the day after a morning star pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_morning_star(days=1825)
            pattern_column = "candle_morning_star"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
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
        prices["candle_morning_star"] = talib.CDLMORNINGSTAR(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_morning_star_doji(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the morning doji star candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_morning_star_doji` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Compare how often the morning doji star pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_morning_star_doji"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_morning_star_doji(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
            ```

            Check whether the latest Nifty candle is a morning doji star pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_morning_star_doji(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_morning_star_doji"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
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
        prices["candle_morning_star_doji"] = talib.CDLMORNINGDOJISTAR(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_on_neck(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the on-neck candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_on_neck` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the on-neck matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_on_neck(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_on_neck"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
            ```

            Print the unadjusted candles of State Bank of India that formed a on-neck pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_on_neck(days=180, adjusted=False)
            pattern_column = "candle_on_neck"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
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
        prices["candle_on_neck"] = talib.CDLONNECK(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_piercing(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the piercing candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_piercing` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Measure the average return on the day after a piercing pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_piercing(days=1825)
            pattern_column = "candle_piercing"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
            ```

            Print the dates in the last year when the piercing pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_piercing(days=365)
            pattern_column = "candle_piercing"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
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
        prices["candle_piercing"] = talib.CDLPIERCING(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_rickshaw_man(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the rickshaw man candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_rickshaw_man` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Check whether the latest Nifty candle is a rickshaw man pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_rickshaw_man(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_rickshaw_man"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
            ```

            Count the bullish and the bearish rickshaw man signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_rickshaw_man(days=730)
            pattern_column = "candle_rickshaw_man"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
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
        prices["candle_rickshaw_man"] = talib.CDLRICKSHAWMAN(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_rise_fall_three_methods(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the rising or falling three methods candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_rise_fall_three_methods` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the unadjusted candles of State Bank of India that formed a rising or falling three methods pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_rise_fall_three_methods(
                days=180,
                adjusted=False,
            )
            pattern_column = "candle_rise_fall_three_methods"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
            ```

            Find the most recent rising or falling three methods pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_rise_fall_three_methods(days=1095)
            pattern_column = "candle_rise_fall_three_methods"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
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
        prices["candle_rise_fall_three_methods"] = talib.CDLRISEFALL3METHODS(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_separating_lines(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the separating lines candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_separating_lines` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the dates in the last year when the separating lines pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_separating_lines(days=365)
            pattern_column = "candle_separating_lines"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
            ```

            Compare how often the separating lines pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_separating_lines"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_separating_lines(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
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
        prices["candle_separating_lines"] = talib.CDLSEPARATINGLINES(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_shooting_star(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the shooting star candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_shooting_star` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the bullish and the bearish shooting star signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_shooting_star(days=730)
            pattern_column = "candle_shooting_star"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
            ```

            Count the shooting star matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_shooting_star(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_shooting_star"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
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
        prices["candle_shooting_star"] = talib.CDLSHOOTINGSTAR(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_short_line(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the short line candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_short_line` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Find the most recent short line pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_short_line(days=1095)
            pattern_column = "candle_short_line"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
            ```

            Measure the average return on the day after a short line pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_short_line(days=1825)
            pattern_column = "candle_short_line"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
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
        prices["candle_short_line"] = talib.CDLSHORTLINE(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_spinning_top(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the spinning top candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_spinning_top` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Compare how often the spinning top pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_spinning_top"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_spinning_top(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
            ```

            Check whether the latest Nifty candle is a spinning top pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_spinning_top(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_spinning_top"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
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
        prices["candle_spinning_top"] = talib.CDLSPINNINGTOP(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_stalled_pattern(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the stalled candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_stalled_pattern` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the stalled matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_stalled_pattern(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_stalled_pattern"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
            ```

            Print the unadjusted candles of State Bank of India that formed a stalled pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_stalled_pattern(
                days=180,
                adjusted=False,
            )
            pattern_column = "candle_stalled_pattern"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
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
        prices["candle_stalled_pattern"] = talib.CDLSTALLEDPATTERN(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_stick_sandwich(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the stick sandwich candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_stick_sandwich` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Measure the average return on the day after a stick sandwich pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_stick_sandwich(days=1825)
            pattern_column = "candle_stick_sandwich"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
            ```

            Print the dates in the last year when the stick sandwich pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_stick_sandwich(days=365)
            pattern_column = "candle_stick_sandwich"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
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
        prices["candle_stick_sandwich"] = talib.CDLSTICKSANDWICH(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_takuri(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the takuri, a dragonfly doji with a very long lower shadow, candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_takuri` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Check whether the latest Nifty candle is a takuri, a dragonfly doji with a very long lower shadow, pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_takuri(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_takuri"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
            ```

            Count the bullish and the bearish takuri, a dragonfly doji with a very long lower shadow, signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_takuri(days=730)
            pattern_column = "candle_takuri"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
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
        prices["candle_takuri"] = talib.CDLTAKURI(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_tasuki_gap(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the tasuki gap candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_tasuki_gap` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the unadjusted candles of State Bank of India that formed a tasuki gap pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_tasuki_gap(
                days=180,
                adjusted=False,
            )
            pattern_column = "candle_tasuki_gap"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
            ```

            Find the most recent tasuki gap pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_tasuki_gap(days=1095)
            pattern_column = "candle_tasuki_gap"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
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
        prices["candle_tasuki_gap"] = talib.CDLTASUKIGAP(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_thrusting_pattern(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the thrusting candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_thrusting_pattern` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the dates in the last year when the thrusting pattern appeared on Infosys, with 100 for bullish and -100 for bearish:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            pattern_frame = infosys.candle_thrusting_pattern(days=365)
            pattern_column = "candle_thrusting_pattern"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in the last year.")
            for position in range(len(matches)):
                row = matches.iloc[position]
                print(row["datetime"].date(), row[pattern_column])
            ```

            Compare how often the thrusting pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_thrusting_pattern"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_thrusting_pattern(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
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
        prices["candle_thrusting_pattern"] = talib.CDLTHRUSTING(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_tristar(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the tristar candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_tristar` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the bullish and the bearish tristar signals on the Nifty index over two years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_tristar(days=730)
            pattern_column = "candle_tristar"
            bullish_count = int((pattern_frame[pattern_column] > 0).sum())
            bearish_count = int((pattern_frame[pattern_column] < 0).sum())
            print(f"Bullish: {bullish_count}, bearish: {bearish_count}")
            ```

            Count the tristar matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_tristar(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_tristar"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
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
        prices["candle_tristar"] = talib.CDLTRISTAR(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_unique_three_river(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the unique three river candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_unique_three_river` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Find the most recent unique three river pattern on Reliance Industries in the last three years:

            ```python
            from tradingmachine.assets import equities

            reliance = equities.Equity(exchange="nse", symbol="RELIANCE")
            pattern_frame = reliance.candle_unique_three_river(days=1095)
            pattern_column = "candle_unique_three_river"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match on Reliance in three years.")
            else:
                latest = matches.iloc[-1]
                latest_date = latest["datetime"].date()
                close_price = latest["close"]
                print(f"Last seen on {latest_date}, closing at {close_price}.")
            ```

            Measure the average return on the day after a unique three river pattern on HDFC Bank over five years:

            ```python
            from tradingmachine.assets import equities

            hdfc_bank = equities.Equity(exchange="nse", symbol="HDFCBANK")
            pattern_frame = hdfc_bank.candle_unique_three_river(days=1825)
            pattern_column = "candle_unique_three_river"
            closes = pattern_frame["close"]
            next_day_return = closes.shift(-1) / closes - 1
            after_pattern = next_day_return[pattern_frame[pattern_column] != 0]
            after_pattern = after_pattern.dropna()
            if after_pattern.empty:
                print("No match with a following day to measure.")
            else:
                average = after_pattern.mean()
                match_count = len(after_pattern)
                print(f"{match_count} matches, {average:.3%} on the next day")
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
        prices["candle_unique_three_river"] = talib.CDLUNIQUE3RIVER(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_up_side_gap_two_crows(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the upside gap two crows candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_up_side_gap_two_crows` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Compare how often the upside gap two crows pattern appeared on three shares over five years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HDFCBANK",
            ]
            pattern_column = "candle_up_side_gap_two_crows"
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                pattern_frame = share.candle_up_side_gap_two_crows(days=1825)
                match_count = int((pattern_frame[pattern_column] != 0).sum())
                print(f"{symbol}: {match_count} matches in five years")
            ```

            Check whether the latest Nifty candle is a upside gap two crows pattern:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            pattern_frame = nifty.candle_up_side_gap_two_crows(days=30)
            latest = pattern_frame.iloc[-1]
            latest_date = latest["datetime"].date()
            signal = latest["candle_up_side_gap_two_crows"]
            if signal > 0:
                print(f"Bullish match on {latest_date}.")
            elif signal < 0:
                print(f"Bearish match on {latest_date}.")
            else:
                print(f"No match on the latest candle, {latest_date}.")
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
        prices["candle_up_side_gap_two_crows"] = talib.CDLUPSIDEGAP2CROWS(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices

    def candle_up_side_down_side_gap_three_methods(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Marks where the upside or downside gap three methods candlestick pattern appears.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame of the candles with a `candle_up_side_gap_three_methods` column added, which is 100 for a bullish match, -100 for a bearish match and 0 otherwise, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Count the upside or downside gap three methods matches on Tata Consultancy Services in each month of 2025:

            ```python
            from tradingmachine.assets import equities

            tcs = equities.Equity(exchange="nse", symbol="TCS")
            pattern_frame = tcs.candle_up_side_down_side_gap_three_methods(
                from_date="2025-01-01",
                to_date="2025-12-31",
            )
            pattern_column = "candle_up_side_gap_three_methods"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            if matches.empty:
                print("No match in 2025.")
            else:
                months = matches["datetime"].dt.strftime("%Y-%m")
                print(months.value_counts().sort_index())
            ```

            Print the unadjusted candles of State Bank of India that formed a upside or downside gap three methods pattern in the last six months:

            ```python
            from tradingmachine.assets import equities

            state_bank = equities.Equity(exchange="nse", symbol="SBIN")
            pattern_frame = state_bank.candle_up_side_down_side_gap_three_methods(
                days=180,
                adjusted=False,
            )
            pattern_column = "candle_up_side_gap_three_methods"
            matches = pattern_frame[pattern_frame[pattern_column] != 0]
            columns = [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                pattern_column,
            ]
            if matches.empty:
                print("No match in the last six months.")
            else:
                print(matches[columns].to_string(index=False))
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
        prices["candle_up_side_gap_three_methods"] = talib.CDLXSIDEGAP3METHODS(
            prices["open"], prices["high"], prices["low"], prices["close"]
        )
        return prices
