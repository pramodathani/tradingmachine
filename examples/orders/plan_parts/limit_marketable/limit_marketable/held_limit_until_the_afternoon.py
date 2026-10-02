"""Build a held limit order that is given up at 15:15 if the book never reaches it.

The program joins `limit_marketable` with a `time_before` condition, so the order is sent only while the morning and early afternoon last, and gives it a lifetime that ends the wait at 15:15. The order is held at the template's own limit price and takes no pricing of its own. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/limit_marketable/limit_marketable/held_limit_until_the_afternoon.py
"""

import json

from tradingmachine.orders.plan_parts import all_conditions
from tradingmachine.orders.plan_parts import lifetime
from tradingmachine.orders.plan_parts import limit_marketable
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import time_before


class HeldLimitUntilAfternoon:
    """A held limit order with a deadline for its wait.

    Attributes:
        deadline: The str time of day the wait ends.
    """

    def __init__(self):
        """Sets the deadline.

        Raises:
            Nothing.
        """
        self.deadline = "15:15"

    def run(self) -> None:
        """Prints the order's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        part = order_part.OrderPart(
            trigger=all_conditions.AllConditions(
                [
                    limit_marketable.LimitMarketable(),
                    time_before.TimeBefore(self.deadline),
                ]
            ),
            lifetime=lifetime.Lifetime(
                at_time=self.deadline,
                applies_to="waiting",
            ),
        )
        print(f"The limit order is held until {self.deadline} at most:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    HeldLimitUntilAfternoon().run()
