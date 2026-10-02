"""Build a group that holds inside a time window when either the bid or the last price reaches a level.

Groups can hold groups. The program puts an `AnyCondition` on the bid or the last price inside an `AllConditions` group with a window from 10:00 to 14:30, and prints the object and how deep the tree goes. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/all_conditions/all_conditions/window_with_either_price.py
"""

import json

from tradingmachine.orders.plan_parts import all_conditions
from tradingmachine.orders.plan_parts import any_condition
from tradingmachine.orders.plan_parts import price_crosses
from tradingmachine.orders.plan_parts import time_after
from tradingmachine.orders.plan_parts import time_before


class WindowWithEitherPrice:
    """A nested group of conditions.

    Attributes:
        group: The tradingmachine.orders.plan_parts.all_conditions.AllConditions the program prints.
    """

    def __init__(self):
        """Builds the group.

        Raises:
            Nothing.
        """
        self.group = all_conditions.AllConditions(
            [
                time_after.TimeAfter("10:00"),
                time_before.TimeBefore("14:30"),
                any_condition.AnyCondition(
                    [
                        price_crosses.PriceCrosses(level=995.0, field="bid"),
                        price_crosses.PriceCrosses(level=995.0, field="last"),
                    ]
                ),
            ]
        )

    def depth(self, document: object) -> int:
        """Counts how many groups deep a condition object goes.

        Args:
            document: The object to measure, a dict, a list or a plain value.

        Returns:
            The int depth, 0 for a plain value.

        Raises:
            Nothing.
        """
        deepest = 0
        if isinstance(document, dict):
            for key, value in document.items():
                inner = self.depth(value)
                if key in ("all", "any"):
                    inner = inner + 1
                deepest = max(deepest, inner)
        if isinstance(document, list):
            for value in document:
                deepest = max(deepest, self.depth(value))
        return deepest

    def run(self) -> None:
        """Prints the group's object and its depth.

        Returns:
            None.

        Raises:
            Nothing.
        """
        document = self.group.document()
        print(json.dumps(document, indent=2))
        print(f"Groups nested: {self.depth(document)}")


if __name__ == "__main__":
    WindowWithEitherPrice().run()
