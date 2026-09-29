"""Report the log returns of a share and an index from the natural logarithm of their closes.

The program reads a year of daily candles for Infosys and for the NIFTY 50 index through `natural_logarithm`, turns the day-to-day differences of the logarithm into log returns, and prints each instrument's total return, its annualised volatility, and its best and worst days. It then checks the result with `exponential` on Vodafone Idea, whose close is small enough for the exponential not to overflow.

Typical usage example:

  .venv/bin/python examples/assets/analysis/math_transforms/math_transforms/log_return_report.py
"""

import math

from tradingmachine.assets import equities


class LogReturnReport:
    """A return and volatility report built on log prices.

    Attributes:
        instruments: A dict mapping a str label to the instrument whose returns are reported.
        days: The int number of days of daily candles to read.
    """

    def __init__(self, days: int = 365):
        """Creates the report over Infosys and NIFTY.

        Args:
            days: The int number of days of daily candles to read.

        Raises:
            Nothing.
        """
        self.instruments = {
            "INFY": equities.Equity(exchange="nse", symbol="INFY"),
            "NIFTY": equities.EquityIndex(exchange="nse", symbol="NIFTY"),
        }
        self.days = days

    def report(self, label: str, instrument) -> None:
        """Prints the return figures of one instrument.

        Args:
            label: The str name printed for the instrument.
            instrument: The tradingmachine.assets.instruments.Instrument whose returns are reported.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        frame = instrument.natural_logarithm(days=self.days)
        if frame is None:
            print(f"{label}: no candles")
            return
        log_returns = frame["ln"].diff().dropna()
        total = math.exp(log_returns.sum()) - 1
        volatility = log_returns.std() * math.sqrt(252)
        best_row = log_returns.idxmax()
        worst_row = log_returns.idxmin()
        best_day = frame.loc[best_row, "datetime"].date()
        worst_day = frame.loc[worst_row, "datetime"].date()
        print(f"{label}: total return {total:+.2%} over {len(log_returns)} days")
        print(f"  annualised volatility {volatility:.2%}")
        print(f"  best day {best_day} {math.exp(log_returns[best_row]) - 1:+.2%}")
        print(f"  worst day {worst_day} {math.exp(log_returns[worst_row]) - 1:+.2%}")

    def check_round_trip(self) -> None:
        """Checks that the logarithm of the exponential gives Vodafone Idea's close back.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        share = equities.Equity(exchange="nse", symbol="IDEA")
        frame = share.exponential(days=30)
        if frame is None:
            print("IDEA: no candles")
            return
        largest_error = 0.0
        for exponential_value, close in zip(frame["exp"], frame["close"]):
            error = abs(math.log(exponential_value) - close)
            if error > largest_error:
                largest_error = error
        print(f"IDEA round trip through exp and ln: largest error {largest_error:.2e}")

    def run(self) -> None:
        """Prints the report for every instrument and the round-trip check.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        for label, instrument in self.instruments.items():
            self.report(label, instrument)
        self.check_round_trip()


if __name__ == "__main__":
    LogReturnReport().run()
