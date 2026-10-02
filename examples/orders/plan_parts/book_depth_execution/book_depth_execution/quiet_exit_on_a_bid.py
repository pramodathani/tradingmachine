"""Build an exit that sells into the first bid large enough, without resting anything in the book beforehand.

The program builds a protecting sell for 1500 units that waits until at least 1000 are bid at or above 1000 rupees across the levels of the book, then strikes for what is shown, and its lifetime ends it at 15:00 if no such bid has appeared. The pricing is a fixed limit at 1000, so a strike that partly fills rests there. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/book_depth_execution/book_depth_execution/quiet_exit_on_a_bid.py
"""

import json

from tradingmachine.orders.plan_parts import book_depth_execution
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import lifetime
from tradingmachine.orders.plan_parts import order_part


class QuietExit:
    """A protecting sell that strikes only into a large enough bid before 15:00.

    Attributes:
        part: The tradingmachine.orders.plan_parts.order_part.OrderPart the program prints.
    """

    def __init__(self):
        """Builds the exit.

        Raises:
            Nothing.
        """
        self.part = order_part.OrderPart(
            side="protect",
            quantity=1500,
            pricing=fixed_pricing.FixedPricing(
                price=1000.0,
                order_type="LIMIT",
            ),
            execution=book_depth_execution.BookDepthExecution(
                limit_price=1000.0,
                minimum_quantity=1000,
            ),
            lifetime=lifetime.Lifetime(at_time="15:00"),
        )

    def run(self) -> None:
        """Prints the exit's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(json.dumps(self.part.document(), indent=2))


if __name__ == "__main__":
    QuietExit().run()
