"""Build a closing-window buy that starts at 15:00, or at once when placed after it.

A plan placed at 15:05 with `time_at` set to 15:00 would be refused, because that time has passed. The program uses `time_from` instead, so the same plan works whether it is placed before the window opens or inside it, and prices the order as a marketable limit. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/time_from/time_from/closing_window_entry.py
"""

import json

from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import time_from


class ClosingWindowEntry:
    """A buy that waits for the closing window to open, or starts at once inside it.

    Attributes:
        window_start: The str time of day the closing window opens.
    """

    def __init__(self):
        """Sets the time the closing window opens.

        Raises:
            Nothing.
        """
        self.window_start = "15:00"

    def run(self) -> None:
        """Prints the order's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        part = order_part.OrderPart(
            trigger=time_from.TimeFrom(self.window_start),
            pricing=marketable_pricing.MarketablePricing(buffer_ticks=1),
        )
        print(f"The order is sent from {self.window_start}, or at once:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    ClosingWindowEntry().run()
