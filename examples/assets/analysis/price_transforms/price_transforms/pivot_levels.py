"""Work out today's classic pivot levels for NIFTY from the last session's typical price.

The program reads the NIFTY 50 index's recent daily candles through `typical_price`, takes the last complete session's typical price as the pivot, and prints the pivot with the first and second resistance and support levels that floor traders derive from it.

Typical usage example:

  .venv/bin/python examples/assets/analysis/price_transforms/price_transforms/pivot_levels.py
"""

from tradingmachine.assets import equities


class PivotLevels:
    """The classic floor pivot levels of an index.

    Attributes:
        index: The tradingmachine.assets.equities.EquityIndex whose levels are worked out.
    """

    def __init__(self):
        """Creates the calculator over the NIFTY 50 index.

        Raises:
            Nothing.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")

    def levels(self, pivot: float, high: float, low: float) -> dict:
        """Derives the resistance and support levels from a pivot.

        Args:
            pivot: The float typical price of the last session.
            high: The float high of the last session.
            low: The float low of the last session.

        Returns:
            A dict mapping the str names `R2`, `R1`, `Pivot`, `S1` and `S2` to float levels, from the highest to the lowest.

        Raises:
            Nothing.
        """
        return {
            "R2": pivot + (high - low),
            "R1": 2 * pivot - low,
            "Pivot": pivot,
            "S1": 2 * pivot - high,
            "S2": pivot - (high - low),
        }

    def run(self) -> None:
        """Reads the last session and prints its pivot levels.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        frame = self.index.typical_price(days=10)
        if frame is None:
            print("UBI has no NIFTY candles for the range.")
            return
        last_session = frame.iloc[-1]
        session_day = last_session["datetime"].date()
        print(f"Pivot levels from the NIFTY session of {session_day}:")
        levels = self.levels(
            pivot=last_session["typ_price"],
            high=last_session["high"],
            low=last_session["low"],
        )
        for name, level in levels.items():
            print(f"{name:<6} {level:>10.2f}")


if __name__ == "__main__":
    PivotLevels().run()
