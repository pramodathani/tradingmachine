"""Compare one RSI mean-reversion strategy across several shares.

The program defines a strategy that buys when the 14-day relative strength index falls below 30 and sells when it rises above 70, backtests it on three years of candles for each of four shares, writes the interactive plot of the best one to the temporary directory, and prints a table of the results.

Typical usage example:

  .venv/bin/python examples/assets/analysis/strategy_backtests/strategy_backtests/relative_strength_strategy_comparison.py
"""

import pathlib
import tempfile

import backtesting
import pandas as pd
import talib

from tradingmachine.assets import equities


class RelativeStrengthReversal(backtesting.Strategy):
    """A strategy that buys oversold dips and sells overbought rallies.

    Attributes:
        oversold_level: The int RSI level below which the strategy buys.
        overbought_level: The int RSI level above which the strategy sells.
    """

    oversold_level = 30
    overbought_level = 70

    def init(self) -> None:
        """Prepares the 14-day relative strength index of the closes.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.strength = self.I(talib.RSI, self.data.Close, 14)

    def next(self) -> None:
        """Buys below the oversold level and closes the position above the overbought level.

        Returns:
            None.

        Raises:
            Nothing.
        """
        if self.strength[-1] < self.oversold_level and not self.position:
            self.buy()
        elif self.strength[-1] > self.overbought_level and self.position:
            self.position.close()


class RelativeStrengthStrategyComparison:
    """A comparison of the RSI reversal strategy across a list of shares.

    Attributes:
        symbols: The list of str nse symbols to backtest.
        plot_path: The pathlib.Path the best share's plot is written to.
    """

    def __init__(self):
        """Creates the comparison over four large nse shares.

        Raises:
            Nothing.
        """
        self.symbols = [
            "INFY",
            "TCS",
            "RELIANCE",
            "HDFCBANK",
        ]
        temporary_directory = pathlib.Path(tempfile.gettempdir())
        self.plot_path = temporary_directory / "relative_strength_best.html"

    def backtest(self, symbol: str, plot_filename: str | None) -> pd.Series | None:
        """Runs the strategy on one share.

        Args:
            symbol: The str nse symbol of the share.
            plot_filename: The str path to write the plot to, or None for no plot.

        Returns:
            A pandas.Series of the backtest's statistics, or None when UBI has no candles.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        share = equities.Equity(exchange="nse", symbol=symbol)
        return share.run_backtest(
            RelativeStrengthReversal,
            cash=1000000,
            commission=0.0003,
            plot_filename=plot_filename,
            days=1095,
        )

    def run(self) -> None:
        """Backtests every share, prints the table and plots the best share.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        rows = {}
        for symbol in self.symbols:
            statistics = self.backtest(symbol, None)
            if statistics is None:
                print(f"{symbol}: no candles")
                continue
            rows[symbol] = {
                "return_percent": statistics["Return [%]"],
                "buy_and_hold_percent": statistics["Buy & Hold Return [%]"],
                "trades": statistics["# Trades"],
                "win_rate_percent": statistics["Win Rate [%]"],
            }
        if not rows:
            print("No share had candles to backtest.")
            return
        table = pd.DataFrame(rows).T
        print(table.round(2))
        best_symbol = table["return_percent"].astype(float).idxmax()
        self.backtest(best_symbol, str(self.plot_path))
        print(f"Best share: {best_symbol}, plot written to {self.plot_path}")


if __name__ == "__main__":
    RelativeStrengthStrategyComparison().run()
