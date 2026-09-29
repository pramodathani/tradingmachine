"""Backtest a moving average crossover strategy on two years of Infosys candles.

The program defines a strategy that goes long when the 10-day simple moving average crosses above the 30-day one and short when it crosses below, runs it through `run_backtest` with a 0.03 percent commission, and prints the main statistics of the result together with the return of simply holding the share.

Typical usage example:

  .venv/bin/python examples/assets/analysis/strategy_backtests/strategy_backtests/moving_average_crossover_backtest.py
"""

import backtesting
import backtesting.lib
import talib

from tradingmachine.assets import equities


class MovingAverageCrossover(backtesting.Strategy):
    """A strategy that follows the crossings of a fast and a slow simple moving average.

    Attributes:
        fast_window: The int number of candles in the fast average.
        slow_window: The int number of candles in the slow average.
    """

    fast_window = 10
    slow_window = 30

    def init(self) -> None:
        """Prepares the two moving averages over the closing prices.

        Returns:
            None.

        Raises:
            Nothing.
        """
        closes = self.data.Close
        self.fast_average = self.I(talib.SMA, closes, self.fast_window)
        self.slow_average = self.I(talib.SMA, closes, self.slow_window)

    def next(self) -> None:
        """Reverses the position whenever the averages cross.

        Returns:
            None.

        Raises:
            Nothing.
        """
        if backtesting.lib.crossover(self.fast_average, self.slow_average):
            self.position.close()
            self.buy()
        elif backtesting.lib.crossover(self.slow_average, self.fast_average):
            self.position.close()
            self.sell()


class MovingAverageCrossoverBacktest:
    """A backtest of the moving average crossover strategy on one share.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the strategy trades.
        starting_cash: The float cash the backtest starts with.
    """

    def __init__(self):
        """Creates the backtest over Infosys on the nse with Rs 1,00,000.

        Raises:
            Nothing.
        """
        self.share = equities.Equity(exchange="nse", symbol="INFY")
        self.starting_cash = 100000.0

    def run(self) -> None:
        """Runs the backtest and prints its main statistics.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        statistics = self.share.run_backtest(
            MovingAverageCrossover,
            cash=self.starting_cash,
            commission=0.0003,
            days=730,
        )
        if statistics is None:
            print("UBI has no Infosys candles for the last two years.")
            return
        measures = [
            "Start",
            "End",
            "Return [%]",
            "Buy & Hold Return [%]",
            "Max. Drawdown [%]",
            "# Trades",
            "Win Rate [%]",
            "Sharpe Ratio",
        ]
        print("Moving average crossover on INFY, 10 and 30 days")
        for measure in measures:
            value = statistics[measure]
            if isinstance(value, float):
                print(f"{measure:<24}{value:.2f}")
            else:
                print(f"{measure:<24}{value}")


if __name__ == "__main__":
    MovingAverageCrossoverBacktest().run()
