"""Tabulate how closely NSE shares follow the NIFTY 50 index.

The program reads a year of daily candles for each share and for the index, and prints each share's latest 60-day beta against NIFTY, its latest 60-day correlation with NIFTY's returns, and the average of that correlation over the year.

Typical usage example:

  .venv/bin/python examples/assets/analysis/statistic_functions/statistic_functions/market_sensitivity_table.py
"""

from tradingmachine.assets import equities


class MarketSensitivityTable:
    """A table of each share's beta and correlation against the index.

    Attributes:
        benchmark: The tradingmachine.assets.equities.EquityIndex the shares are measured against.
        symbols: A list of str NSE symbols of the shares that are measured.
        window: The int number of candles in each beta and correlation window.
        days: The int number of days of daily candles to read.
    """

    def __init__(self, window: int = 60, days: int = 365):
        """Creates the table over five shares measured against NIFTY.

        Args:
            window: The int number of candles in each beta and correlation window.
            days: The int number of days of daily candles to read.

        Raises:
            Nothing.
        """
        self.benchmark = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        self.symbols = [
            "INFY",
            "TCS",
            "HDFCBANK",
            "RELIANCE",
            "IDEA",
        ]
        self.window = window
        self.days = days

    def describe(self, symbol: str) -> str:
        """Measures one share against the benchmark.

        Args:
            symbol: The str NSE symbol of the share.

        Returns:
            A str line with the share's latest beta, latest correlation and average correlation.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        share = equities.Equity(exchange="nse", symbol=symbol)
        beta_frame = share.beta(
            benchmark=self.benchmark,
            window=self.window,
            days=self.days,
        )
        if beta_frame is None:
            return f"{symbol:<10} no candles"
        correlation_frame = share.correlation_coefficient(
            benchmark=self.benchmark,
            window=self.window,
            days=self.days,
        )
        beta = beta_frame[f"beta_{self.window}"].iloc[-1]
        correlation = correlation_frame[f"corr_{self.window}"]
        return (
            f"{symbol:<10} {beta:>6.2f} {correlation.iloc[-1]:>12.2f} "
            f"{correlation.mean():>12.2f}"
        )

    def run(self) -> None:
        """Prints a header and one line per share.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print(f"Measured against NIFTY over {self.window}-day windows:")
        print(f"{'Symbol':<10} {'Beta':>6} {'Correlation':>12} {'Average':>12}")
        for symbol in self.symbols:
            print(self.describe(symbol))


if __name__ == "__main__":
    MarketSensitivityTable().run()
