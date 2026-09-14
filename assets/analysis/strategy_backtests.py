"""Strategy backtests: running a `backtesting` strategy over an instrument's candles.

The class is inherited by `assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  class SmaCross(backtesting.Strategy):
      ...

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  statistics = infosys.run_backtest(SmaCross, cash=100000, days=730)
"""

import datetime

import backtesting
import pandas as pd

from assets.analysis import price_analysis


class StrategyBacktests(price_analysis.PriceAnalysis):
    """Backtests of trading strategies over an instrument's candles."""

    def run_backtest(
        self,
        strategy: type[backtesting.Strategy],
        cash: float = 10000,
        commission: float = 0.0,
        margin: float = 1.0,
        trade_on_close: bool = False,
        hedging: bool = False,
        exclusive_orders: bool = False,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.Series | None:
        """Runs a strategy over the candles in a range and plots the result.

        The plot is written as an HTML file and opened in a browser by `backtesting`.

        Args:
            strategy: The backtesting.Strategy subclass to run.
            cash: The float starting cash.
            commission: The float commission charged on each trade, as a fraction of its value.
            margin: The float margin required, as a fraction, where 1.0 means no leverage.
            trade_on_close: A bool that is True to fill market orders at the current candle's close rather than the next candle's open.
            hedging: A bool that is True to allow long and short trades at the same time.
            exclusive_orders: A bool that is True to close the open trade whenever a new order is placed.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.Series of the backtest's statistics, or None when UBI has no candles for the range.

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
        candles = prices.set_index("datetime")
        candles = candles[
            [
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        ]
        candles.columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]
        backtest = backtesting.Backtest(
            data=candles,
            strategy=strategy,
            cash=cash,
            commission=commission,
            margin=margin,
            trade_on_close=trade_on_close,
            hedging=hedging,
            exclusive_orders=exclusive_orders,
        )
        statistics = backtest.run()
        backtest.plot()
        return statistics
