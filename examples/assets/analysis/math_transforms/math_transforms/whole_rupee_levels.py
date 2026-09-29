"""Show the whole-rupee levels around each share's close and the size of its price.

The program reads a month of daily candles for several NSE shares through `floor`, `ceiling`, `logarithm_base_10` and `square_root`, and prints for each share the whole rupees its latest close sits between, how many digits its price has, and the square root of the close, which some traders use to space round-number levels.

Typical usage example:

  .venv/bin/python examples/assets/analysis/math_transforms/math_transforms/whole_rupee_levels.py
"""

import math

from tradingmachine.assets import equities


class WholeRupeeLevels:
    """A table of the round-number levels around each share's close.

    Attributes:
        symbols: A list of str NSE symbols of the shares that are described.
        days: The int number of days of daily candles to read.
    """

    def __init__(self, days: int = 30):
        """Creates the table over four NSE shares.

        Args:
            days: The int number of days of daily candles to read.

        Raises:
            Nothing.
        """
        self.symbols = [
            "IDEA",
            "ITC",
            "INFY",
            "RELIANCE",
        ]
        self.days = days

    def describe(self, symbol: str) -> str:
        """Describes the levels around one share's latest close.

        Args:
            symbol: The str NSE symbol of the share.

        Returns:
            A str line with the close, the whole rupees around it, the digit count and the square root.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        share = equities.Equity(exchange="nse", symbol=symbol)
        floor_frame = share.floor(days=self.days)
        if floor_frame is None:
            return f"{symbol:<10} no candles"
        close = floor_frame["close"].iloc[-1]
        below = floor_frame["floor"].iloc[-1]
        above = share.ceiling(days=self.days)["ceil"].iloc[-1]
        logarithm = share.logarithm_base_10(days=self.days)["log10"].iloc[-1]
        root = share.square_root(days=self.days)["sqrt"].iloc[-1]
        digits = math.floor(logarithm) + 1
        return (
            f"{symbol:<10} {close:>10.2f} {below:>8.0f} {above:>8.0f} "
            f"{digits:>7} {root:>8.2f}"
        )

    def run(self) -> None:
        """Prints a header and one line per share.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print(
            f"{'Symbol':<10} {'Close':>10} {'Floor':>8} {'Ceiling':>8} "
            f"{'Digits':>7} {'Root':>8}"
        )
        for symbol in self.symbols:
            print(self.describe(symbol))


if __name__ == "__main__":
    WholeRupeeLevels().run()
