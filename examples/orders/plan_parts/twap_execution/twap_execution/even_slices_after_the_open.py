"""Build a buy that waits for the open to settle and then goes in evenly over an hour.

The program builds an order that waits until 09:45 and then sends twelve equal TWAP slices, one every five minutes, each priced two ticks past the offer when it is sent so every slice trades. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/twap_execution/twap_execution/even_slices_after_the_open.py
"""

import json

from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import time_at
from tradingmachine.orders.plan_parts import twap_execution


class TwapAfterTheOpen:
    """A buy sent as twelve TWAP slices from 09:45.

    Attributes:
        execution: The tradingmachine.orders.plan_parts.twap_execution.TwapExecution the order is sent with.
        part: The tradingmachine.orders.plan_parts.order_part.OrderPart the program prints.
    """

    def __init__(self):
        """Builds the order.

        Raises:
            Nothing.
        """
        self.execution = twap_execution.TwapExecution(
            slices=12,
            over_minutes=60,
        )
        self.part = order_part.OrderPart(
            trigger=time_at.TimeAt("09:45"),
            pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
            execution=self.execution,
        )

    def run(self) -> None:
        """Prints the order's object and the gap between slices.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(json.dumps(self.part.document(), indent=2))
        seconds_apart = self.execution.over_minutes * 60 / self.execution.slices
        print(f"One slice every {seconds_apart:.0f} seconds, the first at 09:45.")


if __name__ == "__main__":
    TwapAfterTheOpen().run()
