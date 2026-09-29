"""Strategy backtests: running a `backtesting` strategy over an instrument's candles.

The class is inherited by `tradingmachine.assets.instruments.Instrument`, which supplies `prices`.

Typical usage example:

  class SmaCross(backtesting.Strategy):
      ...

  infosys = instruments.Instrument(exchange="nse", segment="equities", symbol="INFY")
  statistics = infosys.run_backtest(SmaCross, cash=100000, days=730, plot_filename="sma_cross.html")
"""

import datetime

import backtesting
import pandas as pd

from tradingmachine.assets.analysis import price_analysis


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
        plot_filename: str | None = None,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.Series | None:
        """Runs a strategy over the candles in a range, optionally saving a plot of the result.

        Args:
            strategy: The backtesting.Strategy subclass to run.
            cash: The float starting cash.
            commission: The float commission charged on each trade, as a fraction of its value.
            margin: The float margin required, as a fraction, where 1.0 means no leverage.
            trade_on_close: A bool that is True to fill market orders at the current candle's close rather than the next candle's open.
            hedging: A bool that is True to allow long and short trades at the same time.
            exclusive_orders: A bool that is True to close the open trade whenever a new order is placed.
            plot_filename: The str path of an HTML file to write the interactive plot to, or None to skip the plot. The file is not opened.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.Series of the backtest's statistics, or None when UBI has no candles for the range.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Backtest a 10-day and 30-day moving average crossover on two years of Infosys candles:

            ```python
            import backtesting
            import backtesting.lib
            import talib

            from tradingmachine.assets import equities


            class MovingAverageCross(backtesting.Strategy):
                def init(self):
                    self.fast_average = self.I(talib.SMA, self.data.Close, 10)
                    self.slow_average = self.I(talib.SMA, self.data.Close, 30)

                def next(self):
                    fast = self.fast_average
                    slow = self.slow_average
                    if backtesting.lib.crossover(fast, slow):
                        self.position.close()
                        self.buy()
                    elif backtesting.lib.crossover(slow, fast):
                        self.position.close()
                        self.sell()


            infosys = equities.Equity(exchange="nse", symbol="INFY")
            statistics = infosys.run_backtest(
                MovingAverageCross,
                cash=100000,
                days=730,
            )
            return_percent = statistics["Return [%]"]
            trade_count = statistics["# Trades"]
            print(f"Return: {return_percent:.2f}% from {trade_count} trades")
            ```

            Compare buying and holding the Nifty with and without a 0.1 percent commission:

            ```python
            import backtesting

            from tradingmachine.assets import equities


            class BuyAndHold(backtesting.Strategy):
                def init(self):
                    pass

                def next(self):
                    if not self.position:
                        self.buy()


            nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
            commissions = [
                0.0,
                0.001,
            ]
            for commission in commissions:
                statistics = nifty.run_backtest(
                    BuyAndHold,
                    cash=10000000,
                    commission=commission,
                    days=365,
                )
                final_equity = statistics["Equity Final [$]"]
                print(f"Commission {commission}: ends at {final_equity:,.2f}")
            ```

            Backtest an RSI strategy on Tata Consultancy Services over the 2025 calendar year and save the interactive plot:

            ```python
            import pathlib
            import tempfile

            import backtesting
            import talib

            from tradingmachine.assets import equities


            class RelativeStrengthReversal(backtesting.Strategy):
                def init(self):
                    self.strength = self.I(talib.RSI, self.data.Close, 14)

                def next(self):
                    if self.strength[-1] < 30 and not self.position:
                        self.buy()
                    elif self.strength[-1] > 70 and self.position:
                        self.position.close()


            temporary_directory = pathlib.Path(tempfile.gettempdir())
            plot_path = temporary_directory / "tcs_rsi_backtest.html"
            tcs = equities.Equity(exchange="nse", symbol="TCS")
            statistics = tcs.run_backtest(
                RelativeStrengthReversal,
                cash=100000,
                from_date="2025-01-01",
                to_date="2025-12-31",
                plot_filename=str(plot_path),
            )
            measures = [
                "Return [%]",
                "Win Rate [%]",
                "Max. Drawdown [%]",
            ]
            print(statistics[measures])
            print(f"Plot written: {plot_path.exists()}")
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
        if plot_filename is not None:
            backtest.plot(
                results=statistics,
                filename=plot_filename,
                open_browser=False,
            )
        return statistics
