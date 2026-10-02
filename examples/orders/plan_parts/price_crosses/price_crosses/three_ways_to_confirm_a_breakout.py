"""Compare three ways of confirming a breakout before it counts: at once, two last prices in a row, and held for a time.

A breakout that pokes through a level for one trade and falls back is a common false signal. The program builds three `price_crosses` conditions on the same level, the first firing at once on the last price, the second needing two last prices in a row past it, and the third needing the bid to stay past it for fifteen seconds, and prints each. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/price_crosses/price_crosses/three_ways_to_confirm_a_breakout.py
"""

import json

from tradingmachine.orders.plan_parts import price_crosses


class ConfirmedBreakout:
    """Three breakout conditions on one level, each confirmed differently.

    Attributes:
        level: The float breakout level in rupees.
    """

    def __init__(self):
        """Sets the breakout level.

        Raises:
            Nothing.
        """
        self.level = 1010.0

    def conditions(self) -> dict:
        """Builds the three conditions.

        Returns:
            A dict of a str description to the tradingmachine.orders.plan_parts.price_crosses.PriceCrosses it describes.

        Raises:
            Nothing.
        """
        return {
            "at once": price_crosses.PriceCrosses(
                level=self.level,
                direction="at_or_above",
            ),
            "two last prices in a row": price_crosses.PriceCrosses(
                level=self.level,
                direction="at_or_above",
                confirm="double_last",
            ),
            "the bid held for fifteen seconds": price_crosses.PriceCrosses(
                level=self.level,
                direction="at_or_above",
                field="bid",
                confirm="held",
                hold_seconds=15,
            ),
        }

    def run(self) -> None:
        """Prints each condition's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for description, condition in self.conditions().items():
            print(f"Confirmed {description}:")
            print(json.dumps(condition.document(), indent=2))


if __name__ == "__main__":
    ConfirmedBreakout().run()
