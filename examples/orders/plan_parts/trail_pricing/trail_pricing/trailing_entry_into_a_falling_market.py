"""Build a trailing entry: a buy stop that follows a falling market down and fills on the first rebound.

When `TrailPricing` is used on the order's own side rather than `protect`, a buy stop trails the lowest price seen, so the entry is not filled while the price keeps falling and is filled once it rebounds by the trailing distance. The program builds that entry, then protects each fill with a native stop, and prints the plan. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/trail_pricing/trail_pricing/trailing_entry_into_a_falling_market.py
"""

import json

from tradingmachine.orders.plan_parts import native_stop_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part
from tradingmachine.orders.plan_parts import trail_pricing


class TrailingEntry:
    """A trailing buy stop entry followed by a protecting stop.

    Attributes:
        rebound_points: The float rebound in rupees that fills the entry.
    """

    def __init__(self):
        """Sets the rebound distance.

        Raises:
            Nothing.
        """
        self.rebound_points = 4.0

    def run(self) -> None:
        """Prints the plan's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        plan = then_part.ThenPart(
            first=order_part.OrderPart(
                pricing=trail_pricing.TrailPricing(
                    points=self.rebound_points,
                    limit_offset=1.0,
                ),
            ),
            each_fill=order_part.OrderPart(
                side="protect",
                pricing=native_stop_pricing.NativeStopPricing(
                    trigger_price=950.0,
                    limit_price=948.0,
                ),
            ),
        )
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    TrailingEntry().run()
