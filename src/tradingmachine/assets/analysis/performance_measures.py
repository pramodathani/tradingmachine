"""Performance measures: the return, risk and benchmark figures used to judge an investment over a range.

Each public method fetches candles through `prices`, works on the closing prices, and returns one number, or a DataFrame for `drawdowns`, or a pandas Series for `performance_summary`. The class is inherited by `tradingmachine.assets.instruments.Instrument` and by `tradingmachine.asset_baskets.asset_basket.AssetBasket`, which both supply `prices`, so the same Sharpe ratio or drawdown can be asked of one share, an index, a fund or a whole basket.

Returns are the fractional change of the close from one candle to the next. Annual figures scale by the number of candles in a trading year, 252 for `day` candles and the number of candles in 252 sessions of 375 minutes for an intraday interval such as `5minute`. A `risk_free_rate` is an annual fraction, so 6.5 percent is 0.065.

Typical usage example:

  infosys = equities.Equity(exchange="nse", symbol="INFY")
  nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY 50")
  ratio = infosys.sharpe_ratio(risk_free_rate=0.065, days=365)
  worst = infosys.maximum_drawdown(days=730)
  summary = infosys.performance_summary(benchmark=nifty, risk_free_rate=0.065, days=365)
"""

import datetime
import math
import re
import statistics

import pandas as pd

from tradingmachine.assets.analysis import price_analysis

TRADING_DAYS_PER_YEAR = 252

TRADING_MINUTES_PER_DAY = 375

DAY_INTERVAL = "day"

MINUTE_INTERVAL_PATTERN = re.compile(r"^(\d+)minute$")

HISTORICAL_METHOD = "historical"

PARAMETRIC_METHOD = "parametric"


class PerformanceMeasures(price_analysis.PriceAnalysis):
    """Return, risk and benchmark-relative measures calculated from closing prices."""

    def cumulative_return(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates the total growth of the close from the first candle to the last.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float fractional growth, such as 0.12 for 12 percent, or None when there are fewer than two candles.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print how much Infosys grew over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            growth = infosys.cumulative_return(days=365)
            print(f"Infosys over one year: {growth:.2%}")
            ```

            Rank three shares by their total return in the 2025 calendar year:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "RELIANCE",
            ]
            returns = {}
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                returns[symbol] = share.cumulative_return(
                    from_date="2025-01-01",
                    to_date="2025-12-31",
                )
            for symbol in sorted(returns, key=returns.get, reverse=True):
                print(f"{symbol}: {returns[symbol]:.2%}")
            ```
        """
        closes = self._closes(interval, from_date, to_date, days, adjusted)
        if closes is None:
            return None
        return self._cumulative_return_of(closes)

    def annualised_return(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates the compound annual growth rate of the close over the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float annual growth rate, such as 0.15 for 15 percent a year, or None when there are fewer than two candles.

        Raises:
            ValueError: The interval is neither `day` nor a minute interval such as `5minute`.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the compound annual growth rate of the Nifty over five years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            growth_rate = nifty.annualised_return(days=1825)
            print(f"Nifty over five years: {growth_rate:.2%} a year")
            ```

            Compare the annual growth rate of Infosys over one, three and five years:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            periods = [
                365,
                1095,
                1825,
            ]
            for period in periods:
                growth_rate = infosys.annualised_return(days=period)
                print(f"{period} days: {growth_rate:.2%} a year")
            ```
        """
        periods_per_year = self._periods_per_year(interval)
        closes = self._closes(interval, from_date, to_date, days, adjusted)
        if closes is None:
            return None
        return self._annualised_return_of(closes, periods_per_year)

    def annualised_volatility(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates the standard deviation of returns, scaled to a year.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float annual volatility, such as 0.22 for 22 percent, or None when there are fewer than three candles.

        Raises:
            ValueError: The interval is neither `day` nor a minute interval such as `5minute`.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the annual volatility of Infosys over the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            volatility = infosys.annualised_volatility(days=365)
            print(f"Infosys volatility: {volatility:.2%}")
            ```

            Check whether each of three shares swings more than the Nifty does:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "RELIANCE",
            ]
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            index_volatility = nifty.annualised_volatility(days=730)
            print(f"Nifty: {index_volatility:.2%}")
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                volatility = share.annualised_volatility(days=730)
                if volatility > index_volatility:
                    print(f"{symbol}: {volatility:.2%}, more than the index")
                else:
                    print(f"{symbol}: {volatility:.2%}, less than the index")
            ```
        """
        periods_per_year = self._periods_per_year(interval)
        closes = self._closes(interval, from_date, to_date, days, adjusted)
        if closes is None:
            return None
        return self._annualised_volatility_of(
            closes.pct_change().dropna(),
            periods_per_year,
        )

    def sharpe_ratio(
        self,
        risk_free_rate: float = 0.0,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates the Sharpe ratio: the annual return above the risk-free rate for each unit of annual volatility.

        A ratio above 1 is usually thought good. The annual return here is the mean return scaled to a year, which is the textbook form, rather than the compound growth rate `annualised_return` gives.

        Args:
            risk_free_rate: The float annual risk-free rate as a fraction, such as 0.065 for a 6.5 percent treasury bill.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float Sharpe ratio, or None when there are fewer than three candles or the price never moved.

        Raises:
            ValueError: The interval is neither `day` nor a minute interval such as `5minute`.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the Sharpe ratio of Infosys over one year against a 6.5 percent treasury bill:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            ratio = infosys.sharpe_ratio(risk_free_rate=0.065, days=365)
            print(f"Sharpe ratio: {ratio:.2f}")
            ```

            Pick the share with the best risk-adjusted return over two years:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "RELIANCE",
            ]
            best_symbol = None
            best_ratio = None
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                ratio = share.sharpe_ratio(risk_free_rate=0.065, days=730)
                print(f"{symbol}: {ratio:.2f}")
                if best_ratio is None or ratio > best_ratio:
                    best_symbol = symbol
                    best_ratio = ratio
            print(f"Best Sharpe ratio: {best_symbol}")
            ```
        """
        periods_per_year = self._periods_per_year(interval)
        closes = self._closes(interval, from_date, to_date, days, adjusted)
        if closes is None:
            return None
        return self._sharpe_ratio_of(
            closes.pct_change().dropna(),
            risk_free_rate,
            periods_per_year,
        )

    def sortino_ratio(
        self,
        risk_free_rate: float = 0.0,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates the Sortino ratio, which is the Sharpe ratio with only the falls counted as risk.

        The downside deviation is the root mean square of each period's shortfall below the risk-free rate, counting a period that beat it as zero.

        Args:
            risk_free_rate: The float annual risk-free rate as a fraction, such as 0.065.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float Sortino ratio, or None when there are fewer than three candles or no period fell short of the risk-free rate.

        Raises:
            ValueError: The interval is neither `day` nor a minute interval such as `5minute`.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the Sortino ratio of the Nifty over two years against a 6.5 percent risk-free rate:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            ratio = nifty.sortino_ratio(risk_free_rate=0.065, days=730)
            print(f"Nifty Sortino ratio: {ratio:.2f}")
            ```

            Compare the Sortino and Sharpe ratios of Infosys to see whether its falls or its rises drive its volatility:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            sortino = infosys.sortino_ratio(risk_free_rate=0.065, days=365)
            sharpe = infosys.sharpe_ratio(risk_free_rate=0.065, days=365)
            print(f"Sortino {sortino:.2f} against Sharpe {sharpe:.2f}")
            if sortino > sharpe:
                print("The rises are larger than the falls.")
            else:
                print("The falls weigh at least as much as the rises.")
            ```
        """
        periods_per_year = self._periods_per_year(interval)
        closes = self._closes(interval, from_date, to_date, days, adjusted)
        if closes is None:
            return None
        return self._sortino_ratio_of(
            closes.pct_change().dropna(),
            risk_free_rate,
            periods_per_year,
        )

    def drawdowns(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Calculates how far the close stood below its highest earlier close at every candle.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame with `datetime`, `close`, `running_peak` and `drawdown` columns, where `drawdown` is zero at a new peak and negative below one, such as -0.1 for ten percent below, or None when there are fewer than two candles.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print how far Infosys stands below its highest close of the last year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            drawdown_frame = infosys.drawdowns(days=365)
            latest = drawdown_frame.iloc[-1]
            print(f"Close {latest['close']}, peak {latest['running_peak']}")
            print(f"Drawdown from the peak: {latest['drawdown']:.2%}")
            ```

            Count the days the Nifty spent more than five percent below its peak in the last three years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            drawdown_frame = nifty.drawdowns(days=1095)
            deep_days = drawdown_frame[drawdown_frame["drawdown"] < -0.05]
            day_count = len(drawdown_frame)
            print(f"{len(deep_days)} of {day_count} days were 5% down.")
            ```
        """
        prices = self.prices(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if prices is None or len(prices) < 2:
            return None
        frame = prices[
            [
                "datetime",
                "close",
            ]
        ].copy()
        frame["running_peak"] = frame["close"].cummax()
        frame["drawdown"] = frame["close"] / frame["running_peak"] - 1
        return frame.reset_index(drop=True)

    def maximum_drawdown(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Finds the worst fall of the close from an earlier peak in the range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float worst drawdown as a negative fraction, such as -0.25 for a 25 percent fall, zero when the close never fell, or None when there are fewer than two candles.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the worst fall of Infosys from a peak over the last two years:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            worst_fall = infosys.maximum_drawdown(days=730)
            print(f"Maximum drawdown: {worst_fall:.2%}")
            ```

            Compare the worst fall of three shares with the Nifty's in 2025:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "RELIANCE",
            ]
            symbols.append("NIFTY")
            for symbol in symbols:
                if symbol == "NIFTY":
                    instrument = equities.EquityIndex(
                        exchange="nse",
                        symbol=symbol,
                    )
                else:
                    instrument = equities.Equity(exchange="nse", symbol=symbol)
                worst_fall = instrument.maximum_drawdown(
                    from_date="2025-01-01",
                    to_date="2025-12-31",
                )
                print(f"{symbol}: {worst_fall:.2%}")
            ```
        """
        closes = self._closes(interval, from_date, to_date, days, adjusted)
        if closes is None:
            return None
        return self._maximum_drawdown_of(closes)

    def calmar_ratio(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates the Calmar ratio: the compound annual growth rate divided by the size of the worst drawdown.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float Calmar ratio, or None when there are fewer than two candles or the close never fell.

        Raises:
            ValueError: The interval is neither `day` nor a minute interval such as `5minute`.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the Calmar ratio of the Nifty over three years:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            ratio = nifty.calmar_ratio(days=1095)
            print(f"Nifty Calmar ratio: {ratio:.2f}")
            ```

            Show the growth rate and the worst fall that make up the Calmar ratio of Infosys:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            growth_rate = infosys.annualised_return(days=730)
            worst_fall = infosys.maximum_drawdown(days=730)
            ratio = infosys.calmar_ratio(days=730)
            print(f"{growth_rate:.2%} a year, worst fall {worst_fall:.2%}")
            if ratio is None:
                print("The close never fell, so there is no Calmar ratio.")
            else:
                print(f"Calmar ratio: {ratio:.2f}")
            ```
        """
        periods_per_year = self._periods_per_year(interval)
        closes = self._closes(interval, from_date, to_date, days, adjusted)
        if closes is None:
            return None
        return self._calmar_ratio_of(closes, periods_per_year)

    def value_at_risk(
        self,
        confidence: float = 0.95,
        method: str = HISTORICAL_METHOD,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Estimates the loss over one candle that is not exceeded with the given confidence.

        The `historical` method reads the loss straight from the returns in the range. The `parametric` method assumes returns follow a normal distribution with the range's mean and standard deviation, which understates the rare large falls real prices have.

        Args:
            confidence: The float confidence level between 0 and 1, such as 0.95 for the loss exceeded on only one candle in twenty.
            method: The str method, `historical` or `parametric`.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float loss as a positive fraction of the value, such as 0.021 for 2.1 percent, or None when there are fewer than three candles.

        Raises:
            ValueError: The method is neither `historical` nor `parametric`, or confidence is not between 0 and 1.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the one-day loss Infosys should not exceed on 95 days in 100, from a year of history:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            loss = infosys.value_at_risk(confidence=0.95, days=365)
            print(f"One-day value at risk: {loss:.2%}")
            ```

            Compare the historical and parametric value at risk of the Nifty at 99 percent confidence:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            methods = [
                "historical",
                "parametric",
            ]
            for method in methods:
                loss = nifty.value_at_risk(
                    confidence=0.99,
                    method=method,
                    days=1095,
                )
                print(f"{method}: {loss:.2%}")
            ```

            Turn the value at risk of Infosys into rupees for a holding worth Rs 5,00,000:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            holding_value = 500000
            loss = infosys.value_at_risk(confidence=0.95, days=730)
            loss_in_rupees = holding_value * loss
            print(f"Loss under Rs {loss_in_rupees:,.0f} on 19 days in 20")
            ```
        """
        self._check_value_at_risk_arguments(confidence, method)
        closes = self._closes(interval, from_date, to_date, days, adjusted)
        if closes is None:
            return None
        return self._value_at_risk_of(
            closes.pct_change().dropna(),
            confidence,
            method,
        )

    def expected_shortfall(
        self,
        confidence: float = 0.95,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates the average loss over one candle on the candles whose loss reached the historical value at risk.

        This is also called the conditional value at risk. It answers how bad the bad days are, where the value at risk only says where they begin.

        Args:
            confidence: The float confidence level between 0 and 1, such as 0.95.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float average loss as a positive fraction, or None when there are fewer than three candles.

        Raises:
            ValueError: confidence is not between 0 and 1.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the average loss of Infosys on its worst five percent of days over one year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            shortfall = infosys.expected_shortfall(confidence=0.95, days=365)
            print(f"Expected shortfall: {shortfall:.2%}")
            ```

            Show how much worse the Nifty's bad days are than where they begin:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            loss = nifty.value_at_risk(confidence=0.95, days=1095)
            shortfall = nifty.expected_shortfall(confidence=0.95, days=1095)
            print(f"Bad days begin at a loss of {loss:.2%}")
            print(f"They average a loss of {shortfall:.2%}")
            ```
        """
        self._check_value_at_risk_arguments(confidence, HISTORICAL_METHOD)
        closes = self._closes(interval, from_date, to_date, days, adjusted)
        if closes is None:
            return None
        return self._expected_shortfall_of(
            closes.pct_change().dropna(),
            confidence,
        )

    def benchmark_beta(
        self,
        benchmark: price_analysis.PriceAnalysis,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates one beta against a benchmark over the whole range.

        This is the slope of the returns regressed on the benchmark's returns, so 1.2 means the price tended to move 1.2 percent for each percent the benchmark moved. `beta` gives the rolling TA-Lib version instead.

        Args:
            benchmark: The object to measure against, such as an index instrument or a basket, or anything else with a `prices` method.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float beta, or None when fewer than three candles match the benchmark's or the benchmark never moved.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the beta of Infosys against the Nifty over two years:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            beta = infosys.benchmark_beta(nifty, days=730)
            print(f"Infosys beta against the Nifty: {beta:.2f}")
            ```

            Sort three shares into defensive and aggressive by their beta:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "RELIANCE",
            ]
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                beta = share.benchmark_beta(nifty, days=365)
                if beta < 1:
                    print(f"{symbol}: beta {beta:.2f}, defensive")
                else:
                    print(f"{symbol}: beta {beta:.2f}, aggressive")
            ```
        """
        matched = self._matched_returns(
            benchmark, interval, from_date, to_date, days, adjusted
        )
        if matched is None:
            return None
        return self._beta_of(matched)

    def alpha(
        self,
        benchmark: price_analysis.PriceAnalysis,
        risk_free_rate: float = 0.0,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates Jensen's alpha: the annual return beyond what the benchmark's moves and the beta explain.

        Args:
            benchmark: The object to measure against, such as an index instrument or a basket, or anything else with a `prices` method.
            risk_free_rate: The float annual risk-free rate as a fraction, such as 0.065.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float annual alpha as a fraction, such as 0.03 for three percent a year ahead, or None when fewer than three candles match or the benchmark never moved.

        Raises:
            ValueError: The interval is neither `day` nor a minute interval such as `5minute`.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the annual alpha of Infosys against the Nifty over one year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            excess = infosys.alpha(nifty, risk_free_rate=0.065, days=365)
            print(f"Jensen's alpha: {excess:.2%} a year")
            ```

            Find which of three shares beat the Nifty after allowing for its beta in 2025:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "RELIANCE",
            ]
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                excess = share.alpha(
                    nifty,
                    risk_free_rate=0.065,
                    from_date="2025-01-01",
                    to_date="2025-12-31",
                )
                print(f"{symbol}: alpha {excess:.2%}")
            ```
        """
        periods_per_year = self._periods_per_year(interval)
        matched = self._matched_returns(
            benchmark, interval, from_date, to_date, days, adjusted
        )
        if matched is None:
            return None
        return self._alpha_of(matched, risk_free_rate, periods_per_year)

    def tracking_error(
        self,
        benchmark: price_analysis.PriceAnalysis,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates the annual volatility of the difference between the returns and the benchmark's.

        A fund that follows an index closely has a tracking error near zero.

        Args:
            benchmark: The object to measure against, such as an index instrument or a basket, or anything else with a `prices` method.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float annual tracking error as a fraction, or None when fewer than three candles match the benchmark's.

        Raises:
            ValueError: The interval is neither `day` nor a minute interval such as `5minute`.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Measure how closely the Nifty BeES exchange-traded fund followed the Nifty over one year:

            ```python
            from tradingmachine.assets import equities
            from tradingmachine.assets import funds

            nifty_bees = funds.ExchangeTradedFund(
                exchange="nse",
                symbol="NIFTYBEES",
            )
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            error = nifty_bees.tracking_error(nifty, days=365)
            print(f"Tracking error: {error:.2%}")
            ```

            Compare the tracking error of Infosys and Reliance Industries against the Nifty:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            symbols = [
                "INFY",
                "RELIANCE",
            ]
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                error = share.tracking_error(nifty, days=730)
                print(f"{symbol}: {error:.2%}")
            ```
        """
        periods_per_year = self._periods_per_year(interval)
        matched = self._matched_returns(
            benchmark, interval, from_date, to_date, days, adjusted
        )
        if matched is None:
            return None
        return self._tracking_error_of(matched, periods_per_year)

    def information_ratio(
        self,
        benchmark: price_analysis.PriceAnalysis,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates the information ratio: the annual return above the benchmark for each unit of tracking error.

        Args:
            benchmark: The object to measure against, such as an index instrument or a basket, or anything else with a `prices` method.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float information ratio, or None when fewer than three candles match the benchmark's or the returns never differed from it.

        Raises:
            ValueError: The interval is neither `day` nor a minute interval such as `5minute`.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print the information ratio of Infosys against the Nifty over two years:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            ratio = infosys.information_ratio(nifty, days=730)
            print(f"Information ratio: {ratio:.2f}")
            ```

            Check whether each of three shares beat the Nifty consistently over one year, taking a ratio above 0.5 as consistent:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "RELIANCE",
            ]
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                ratio = share.information_ratio(nifty, days=365)
                if ratio > 0.5:
                    print(f"{symbol}: {ratio:.2f}, consistently ahead")
                else:
                    print(f"{symbol}: {ratio:.2f}, not consistently ahead")
            ```
        """
        periods_per_year = self._periods_per_year(interval)
        matched = self._matched_returns(
            benchmark, interval, from_date, to_date, days, adjusted
        )
        if matched is None:
            return None
        return self._information_ratio_of(matched, periods_per_year)

    def up_capture_ratio(
        self,
        benchmark: price_analysis.PriceAnalysis,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates how much of the benchmark's rises were captured, on the candles where the benchmark rose.

        Args:
            benchmark: The object to measure against, such as an index instrument or a basket, or anything else with a `prices` method.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float ratio of the mean return to the benchmark's mean return on those candles, such as 1.1 for rising ten percent more, or None when fewer than three candles match or the benchmark never rose.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print how much of the Nifty's rises Infosys captured over one year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            ratio = infosys.up_capture_ratio(nifty, days=365)
            print(f"Up capture: {ratio:.2f}")
            ```

            Put the up and down capture ratios of Tata Consultancy Services side by side:

            ```python
            from tradingmachine.assets import equities

            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            tcs = equities.Equity(exchange="nse", symbol="TCS")
            up_ratio = tcs.up_capture_ratio(nifty, days=730)
            down_ratio = tcs.down_capture_ratio(nifty, days=730)
            print(f"Up capture {up_ratio:.2f}, down capture {down_ratio:.2f}")
            if up_ratio > down_ratio:
                print("TCS caught more of the rises than of the falls.")
            else:
                print("TCS caught no more of the rises than of the falls.")
            ```
        """
        matched = self._matched_returns(
            benchmark, interval, from_date, to_date, days, adjusted
        )
        if matched is None:
            return None
        return self._capture_ratio_of(matched, rising=True)

    def down_capture_ratio(
        self,
        benchmark: price_analysis.PriceAnalysis,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates how much of the benchmark's falls were suffered, on the candles where the benchmark fell.

        Args:
            benchmark: The object to measure against, such as an index instrument or a basket, or anything else with a `prices` method.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float ratio of the mean return to the benchmark's mean return on those candles, where below 1 means falling less than the benchmark, or None when fewer than three candles match or the benchmark never fell.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print how much of the Nifty's falls Infosys suffered over one year:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            ratio = infosys.down_capture_ratio(nifty, days=365)
            print(f"Down capture: {ratio:.2f}")
            ```

            Find the share among three that fell least when the Nifty fell in 2025:

            ```python
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "RELIANCE",
            ]
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            safest_symbol = None
            lowest_ratio = None
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                ratio = share.down_capture_ratio(
                    nifty,
                    from_date="2025-01-01",
                    to_date="2025-12-31",
                )
                print(f"{symbol}: {ratio:.2f}")
                if lowest_ratio is None or ratio < lowest_ratio:
                    safest_symbol = symbol
                    lowest_ratio = ratio
            print(f"Fell least with the index: {safest_symbol}")
            ```
        """
        matched = self._matched_returns(
            benchmark, interval, from_date, to_date, days, adjusted
        )
        if matched is None:
            return None
        return self._capture_ratio_of(matched, rising=False)

    def performance_summary(
        self,
        benchmark: price_analysis.PriceAnalysis | None = None,
        risk_free_rate: float = 0.0,
        confidence: float = 0.95,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.Series | None:
        """Calculates every measure in this class from one fetch of the candles.

        Args:
            benchmark: The object to measure against, such as an index instrument or a basket, or None to leave out the benchmark measures.
            risk_free_rate: The float annual risk-free rate as a fraction, such as 0.065.
            confidence: The float confidence level for the value at risk and expected shortfall, such as 0.95.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.Series indexed by measure name, from `cumulative_return` to `expected_shortfall` and, when a benchmark is given, `benchmark_beta` to `down_capture_ratio`, where a measure that cannot be calculated is None; or None when there are fewer than two candles.

        Raises:
            ValueError: The interval is neither `day` nor a minute interval such as `5minute`, or confidence is not between 0 and 1.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Print every measure for Infosys over one year, without a benchmark:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            summary = infosys.performance_summary(
                risk_free_rate=0.065,
                days=365,
            )
            print(summary)
            ```

            Print every measure for Infosys against the Nifty over two years, including the benchmark measures:

            ```python
            from tradingmachine.assets import equities

            infosys = equities.Equity(exchange="nse", symbol="INFY")
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            summary = infosys.performance_summary(
                benchmark=nifty,
                risk_free_rate=0.065,
                confidence=0.99,
                days=730,
            )
            print(summary.to_string())
            ```

            Build a table comparing three shares on a few of the measures:

            ```python
            import pandas as pd

            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "RELIANCE",
            ]
            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            summaries = {}
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                summaries[symbol] = share.performance_summary(
                    benchmark=nifty,
                    risk_free_rate=0.065,
                    days=365,
                )
            table = pd.DataFrame(summaries)
            measures = [
                "annualised_return",
                "sharpe_ratio",
                "maximum_drawdown",
                "benchmark_beta",
            ]
            print(table.loc[measures])
            ```
        """
        periods_per_year = self._periods_per_year(interval)
        self._check_value_at_risk_arguments(confidence, HISTORICAL_METHOD)
        closes = self._closes(interval, from_date, to_date, days, adjusted)
        if closes is None:
            return None
        returns = closes.pct_change().dropna()
        summary = {
            "cumulative_return": self._cumulative_return_of(closes),
            "annualised_return": self._annualised_return_of(closes, periods_per_year),
            "annualised_volatility": self._annualised_volatility_of(
                returns, periods_per_year
            ),
            "sharpe_ratio": self._sharpe_ratio_of(
                returns, risk_free_rate, periods_per_year
            ),
            "sortino_ratio": self._sortino_ratio_of(
                returns, risk_free_rate, periods_per_year
            ),
            "maximum_drawdown": self._maximum_drawdown_of(closes),
            "calmar_ratio": self._calmar_ratio_of(closes, periods_per_year),
            "value_at_risk": self._value_at_risk_of(
                returns, confidence, HISTORICAL_METHOD
            ),
            "expected_shortfall": self._expected_shortfall_of(returns, confidence),
        }
        if benchmark is not None:
            matched = self._matched_returns(
                benchmark, interval, from_date, to_date, days, adjusted
            )
            if matched is None:
                summary["benchmark_beta"] = None
                summary["alpha"] = None
                summary["tracking_error"] = None
                summary["information_ratio"] = None
                summary["up_capture_ratio"] = None
                summary["down_capture_ratio"] = None
            else:
                summary["benchmark_beta"] = self._beta_of(matched)
                summary["alpha"] = self._alpha_of(
                    matched, risk_free_rate, periods_per_year
                )
                summary["tracking_error"] = self._tracking_error_of(
                    matched, periods_per_year
                )
                summary["information_ratio"] = self._information_ratio_of(
                    matched, periods_per_year
                )
                summary["up_capture_ratio"] = self._capture_ratio_of(
                    matched, rising=True
                )
                summary["down_capture_ratio"] = self._capture_ratio_of(
                    matched, rising=False
                )
        return pd.Series(summary, dtype=object)

    @staticmethod
    def _periods_per_year(interval: str) -> float:
        """Counts the candles of an interval in one trading year.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.

        Returns:
            The float number of candles in 252 trading sessions of 375 minutes each.

        Raises:
            ValueError: The interval is neither `day` nor a minute interval such as `5minute`.
        """
        if interval == DAY_INTERVAL:
            return float(TRADING_DAYS_PER_YEAR)
        match = MINUTE_INTERVAL_PATTERN.match(interval)
        if match is None:
            raise ValueError(f"Cannot annualise candles of this interval: {interval=}")
        minutes = int(match.group(1))
        return TRADING_DAYS_PER_YEAR * TRADING_MINUTES_PER_DAY / minutes

    @staticmethod
    def _check_value_at_risk_arguments(confidence: float, method: str) -> None:
        """Checks a confidence level and a value at risk method.

        Args:
            confidence: The float confidence level, which must lie strictly between 0 and 1.
            method: The str method, which must be `historical` or `parametric`.

        Returns:
            None.

        Raises:
            ValueError: The confidence or the method is not valid.
        """
        if not 0 < confidence < 1:
            raise ValueError(f"Not a confidence level between 0 and 1: {confidence=}")
        if method not in (HISTORICAL_METHOD, PARAMETRIC_METHOD):
            raise ValueError(f"Not a value at risk method: {method=}")

    def _closes(
        self,
        interval: str,
        from_date: datetime.date | str | None,
        to_date: datetime.date | str | None,
        days: int | None,
        adjusted: bool,
    ) -> pd.Series | None:
        """Fetches the closing prices for a range.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.Series of float closes in time order, or None when there are fewer than two candles.

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
        closes = prices["close"].astype(float).dropna().reset_index(drop=True)
        if len(closes) < 2:
            return None
        return closes

    def _matched_returns(
        self,
        benchmark: price_analysis.PriceAnalysis,
        interval: str,
        from_date: datetime.date | str | None,
        to_date: datetime.date | str | None,
        days: int | None,
        adjusted: bool,
    ) -> pd.DataFrame | None:
        """Fetches the returns and a benchmark's returns on the candles both have.

        Args:
            benchmark: The object with a `prices` method to match against.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame with float `returns` and `benchmark_returns` columns, one row per matched candle after the first, or None when fewer than three candles match.

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
        own_closes = prices[
            [
                "datetime",
                "close",
            ]
        ]
        benchmark_closes = benchmark_prices[
            [
                "datetime",
                "close",
            ]
        ].rename(columns={"close": "benchmark_close"})
        matched = own_closes.merge(benchmark_closes, on="datetime", how="inner")
        matched = matched.sort_values("datetime").dropna()
        if len(matched) < 3:
            return None
        returns = pd.DataFrame(
            {
                "returns": matched["close"].astype(float).pct_change(),
                "benchmark_returns": matched["benchmark_close"]
                .astype(float)
                .pct_change(),
            }
        )
        return returns.dropna().reset_index(drop=True)

    @staticmethod
    def _cumulative_return_of(closes: pd.Series) -> float:
        """Calculates the growth from the first close to the last.

        Args:
            closes: A pandas.Series of at least two float closes in time order.

        Returns:
            The float fractional growth.

        Raises:
            Nothing.
        """
        return float(closes.iloc[-1] / closes.iloc[0] - 1)

    @staticmethod
    def _annualised_return_of(
        closes: pd.Series,
        periods_per_year: float,
    ) -> float | None:
        """Calculates the compound annual growth rate of a run of closes.

        Args:
            closes: A pandas.Series of at least two float closes in time order.
            periods_per_year: The float number of candles in a trading year.

        Returns:
            The float annual growth rate, or None when the first close is not positive.

        Raises:
            Nothing.
        """
        if closes.iloc[0] <= 0 or closes.iloc[-1] <= 0:
            return None
        growth = closes.iloc[-1] / closes.iloc[0]
        years = (len(closes) - 1) / periods_per_year
        return float(growth ** (1 / years) - 1)

    @staticmethod
    def _annualised_volatility_of(
        returns: pd.Series,
        periods_per_year: float,
    ) -> float | None:
        """Scales the standard deviation of returns to a year.

        Args:
            returns: A pandas.Series of float returns.
            periods_per_year: The float number of candles in a trading year.

        Returns:
            The float annual volatility, or None when there are fewer than two returns.

        Raises:
            Nothing.
        """
        if len(returns) < 2:
            return None
        return float(returns.std() * math.sqrt(periods_per_year))

    @staticmethod
    def _sharpe_ratio_of(
        returns: pd.Series,
        risk_free_rate: float,
        periods_per_year: float,
    ) -> float | None:
        """Calculates the Sharpe ratio of a run of returns.

        Args:
            returns: A pandas.Series of float returns.
            risk_free_rate: The float annual risk-free rate as a fraction.
            periods_per_year: The float number of candles in a trading year.

        Returns:
            The float Sharpe ratio, or None when there are fewer than two returns or they never varied.

        Raises:
            Nothing.
        """
        if len(returns) < 2:
            return None
        volatility = returns.std() * math.sqrt(periods_per_year)
        if volatility == 0:
            return None
        annual_return = returns.mean() * periods_per_year
        return float((annual_return - risk_free_rate) / volatility)

    @staticmethod
    def _sortino_ratio_of(
        returns: pd.Series,
        risk_free_rate: float,
        periods_per_year: float,
    ) -> float | None:
        """Calculates the Sortino ratio of a run of returns.

        Args:
            returns: A pandas.Series of float returns.
            risk_free_rate: The float annual risk-free rate as a fraction.
            periods_per_year: The float number of candles in a trading year.

        Returns:
            The float Sortino ratio, or None when there are fewer than two returns or none fell short of the risk-free rate.

        Raises:
            Nothing.
        """
        if len(returns) < 2:
            return None
        risk_free_per_period = risk_free_rate / periods_per_year
        shortfalls = (returns - risk_free_per_period).clip(upper=0)
        downside_deviation = math.sqrt((shortfalls**2).mean()) * math.sqrt(
            periods_per_year
        )
        if downside_deviation == 0:
            return None
        annual_return = returns.mean() * periods_per_year
        return float((annual_return - risk_free_rate) / downside_deviation)

    @staticmethod
    def _maximum_drawdown_of(closes: pd.Series) -> float:
        """Finds the worst fall of a run of closes from an earlier peak.

        Args:
            closes: A pandas.Series of float closes in time order.

        Returns:
            The float worst drawdown as a negative fraction, or zero when the closes never fell.

        Raises:
            Nothing.
        """
        drawdown = closes / closes.cummax() - 1
        return float(drawdown.min())

    def _calmar_ratio_of(
        self,
        closes: pd.Series,
        periods_per_year: float,
    ) -> float | None:
        """Calculates the Calmar ratio of a run of closes.

        Args:
            closes: A pandas.Series of at least two float closes in time order.
            periods_per_year: The float number of candles in a trading year.

        Returns:
            The float Calmar ratio, or None when the closes never fell or the growth rate cannot be calculated.

        Raises:
            Nothing.
        """
        worst = self._maximum_drawdown_of(closes)
        if worst == 0:
            return None
        annual_return = self._annualised_return_of(closes, periods_per_year)
        if annual_return is None:
            return None
        return annual_return / abs(worst)

    @staticmethod
    def _value_at_risk_of(
        returns: pd.Series,
        confidence: float,
        method: str,
    ) -> float | None:
        """Estimates the one-candle value at risk of a run of returns.

        Args:
            returns: A pandas.Series of float returns.
            confidence: The float confidence level between 0 and 1.
            method: The str method, `historical` or `parametric`.

        Returns:
            The float loss as a positive fraction, or None when there are fewer than two returns.

        Raises:
            Nothing.
        """
        if len(returns) < 2:
            return None
        if method == HISTORICAL_METHOD:
            return float(-returns.quantile(1 - confidence))
        standard_score = statistics.NormalDist().inv_cdf(1 - confidence)
        return float(-(returns.mean() + standard_score * returns.std()))

    def _expected_shortfall_of(
        self,
        returns: pd.Series,
        confidence: float,
    ) -> float | None:
        """Calculates the average loss beyond the historical value at risk of a run of returns.

        Args:
            returns: A pandas.Series of float returns.
            confidence: The float confidence level between 0 and 1.

        Returns:
            The float average loss as a positive fraction, or None when there are fewer than two returns.

        Raises:
            Nothing.
        """
        value_at_risk = self._value_at_risk_of(returns, confidence, HISTORICAL_METHOD)
        if value_at_risk is None:
            return None
        tail = returns[returns <= -value_at_risk]
        return float(-tail.mean())

    @staticmethod
    def _beta_of(matched: pd.DataFrame) -> float | None:
        """Calculates the regression beta of matched returns.

        Args:
            matched: A pandas.DataFrame with `returns` and `benchmark_returns` columns.

        Returns:
            The float beta, or None when the benchmark's returns never varied.

        Raises:
            Nothing.
        """
        benchmark_variance = matched["benchmark_returns"].var()
        if benchmark_variance == 0:
            return None
        covariance = matched["returns"].cov(matched["benchmark_returns"])
        return float(covariance / benchmark_variance)

    def _alpha_of(
        self,
        matched: pd.DataFrame,
        risk_free_rate: float,
        periods_per_year: float,
    ) -> float | None:
        """Calculates Jensen's alpha of matched returns.

        Args:
            matched: A pandas.DataFrame with `returns` and `benchmark_returns` columns.
            risk_free_rate: The float annual risk-free rate as a fraction.
            periods_per_year: The float number of candles in a trading year.

        Returns:
            The float annual alpha, or None when the benchmark's returns never varied.

        Raises:
            Nothing.
        """
        beta = self._beta_of(matched)
        if beta is None:
            return None
        annual_return = matched["returns"].mean() * periods_per_year
        benchmark_annual_return = matched["benchmark_returns"].mean() * periods_per_year
        expected = risk_free_rate + beta * (benchmark_annual_return - risk_free_rate)
        return float(annual_return - expected)

    @staticmethod
    def _tracking_error_of(
        matched: pd.DataFrame,
        periods_per_year: float,
    ) -> float:
        """Calculates the annual tracking error of matched returns.

        Args:
            matched: A pandas.DataFrame with `returns` and `benchmark_returns` columns.
            periods_per_year: The float number of candles in a trading year.

        Returns:
            The float annual tracking error.

        Raises:
            Nothing.
        """
        difference = matched["returns"] - matched["benchmark_returns"]
        return float(difference.std() * math.sqrt(periods_per_year))

    def _information_ratio_of(
        self,
        matched: pd.DataFrame,
        periods_per_year: float,
    ) -> float | None:
        """Calculates the information ratio of matched returns.

        Args:
            matched: A pandas.DataFrame with `returns` and `benchmark_returns` columns.
            periods_per_year: The float number of candles in a trading year.

        Returns:
            The float information ratio, or None when the returns never differed from the benchmark's.

        Raises:
            Nothing.
        """
        tracking_error = self._tracking_error_of(matched, periods_per_year)
        if tracking_error == 0:
            return None
        difference = matched["returns"] - matched["benchmark_returns"]
        return float(difference.mean() * periods_per_year / tracking_error)

    @staticmethod
    def _capture_ratio_of(matched: pd.DataFrame, rising: bool) -> float | None:
        """Calculates the up or down capture ratio of matched returns.

        Args:
            matched: A pandas.DataFrame with `returns` and `benchmark_returns` columns.
            rising: A bool that is True for the candles where the benchmark rose and False for those where it fell.

        Returns:
            The float capture ratio, or None when the benchmark had no such candle.

        Raises:
            Nothing.
        """
        if rising:
            chosen = matched[matched["benchmark_returns"] > 0]
        else:
            chosen = matched[matched["benchmark_returns"] < 0]
        if chosen.empty:
            return None
        benchmark_mean = chosen["benchmark_returns"].mean()
        return float(chosen["returns"].mean() / benchmark_mean)
