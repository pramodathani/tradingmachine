"""Check how faithfully two Nifty exchange-traded funds follow the index.

The program measures NIFTYBEES and SETFNIF50 against the Nifty over one year with `tracking_error`, `benchmark_beta`, `up_capture_ratio`, `down_capture_ratio` and `cumulative_return`, and prints one row per fund, so the fund that follows the index most closely stands out.

Typical usage example:

  .venv/bin/python examples/assets/analysis/performance_measures/performance_measures/index_fund_tracking.py
"""

import pandas as pd

from tradingmachine.assets import equities
from tradingmachine.assets import funds


class IndexFundTracking:
    """A comparison of index funds with the index they follow.

    Attributes:
        benchmark: The tradingmachine.assets.equities.EquityIndex the funds follow.
        fund_symbols: The list of str nse symbols of the funds.
        days: The int number of days the comparison covers.
    """

    def __init__(self):
        """Creates the comparison of two Nifty funds over one year.

        Raises:
            Nothing.
        """
        self.benchmark = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        self.fund_symbols = [
            "NIFTYBEES",
            "SETFNIF50",
        ]
        self.days = 365

    def measure(self, symbol: str) -> dict[str, float | None]:
        """Measures one fund against the benchmark.

        Args:
            symbol: The str nse symbol of the fund.

        Returns:
            A dict mapping each str measure name to its float value, or to None when it cannot be calculated.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI has no fund for the symbol.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        fund = funds.ExchangeTradedFund(exchange="nse", symbol=symbol)
        return {
            "cumulative_return": fund.cumulative_return(days=self.days),
            "tracking_error": fund.tracking_error(
                self.benchmark,
                days=self.days,
            ),
            "beta": fund.benchmark_beta(self.benchmark, days=self.days),
            "up_capture": fund.up_capture_ratio(
                self.benchmark,
                days=self.days,
            ),
            "down_capture": fund.down_capture_ratio(
                self.benchmark,
                days=self.days,
            ),
        }

    def run(self) -> None:
        """Measures every fund and prints the comparison table.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        index_return = self.benchmark.cumulative_return(days=self.days)
        print(f"NIFTY return over {self.days} days: {index_return:.2%}")
        rows = {}
        for symbol in self.fund_symbols:
            rows[symbol] = self.measure(symbol)
        table = pd.DataFrame(rows).T
        print(table.astype(float).round(4))
        closest = table["tracking_error"].astype(float).idxmin()
        print(f"Closest to the index: {closest}")


if __name__ == "__main__":
    IndexFundTracking().run()
