"""Build a breakout that buys above a range or sells below it, whichever happens first.

The program builds an either join with the sibling rule `cancel` around a range from 990 to 1010. A buy waits for the price to reach the top and a sell for it to reach the bottom; the first to fill cancels the other, and with `cancel_before_send` the one whose trigger holds clears its sibling before it is sent, so both can never fill. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/either_part/either_part/breakout_on_either_side.py
"""

import json

from tradingmachine.orders.plan_parts import either_part
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses


class RangeBreakout:
    """A buy above a range and a sell below it, where the first cancels the other.

    Attributes:
        range_low: The float bottom of the range in rupees.
        range_high: The float top of the range in rupees.
    """

    def __init__(self):
        """Sets the range.

        Raises:
            Nothing.
        """
        self.range_low = 990.0
        self.range_high = 1010.0

    def build_join(self) -> either_part.EitherPart:
        """Builds the two breakout orders as one either join.

        Returns:
            The tradingmachine.orders.plan_parts.either_part.EitherPart.

        Raises:
            Nothing.
        """
        return either_part.EitherPart(
            children=[
                order_part.OrderPart(
                    side="buy",
                    trigger=price_crosses.PriceCrosses(
                        level=self.range_high,
                        direction="at_or_above",
                    ),
                    pricing=marketable_pricing.MarketablePricing(),
                ),
                order_part.OrderPart(
                    side="sell",
                    trigger=price_crosses.PriceCrosses(
                        level=self.range_low,
                        direction="at_or_below",
                    ),
                    pricing=marketable_pricing.MarketablePricing(),
                ),
            ],
            sibling_rule="cancel",
            cancel_before_send=True,
        )

    def run(self) -> None:
        """Prints the range and the join's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(f"Range: {self.range_low} to {self.range_high}")
        print(json.dumps(self.build_join().document(), indent=2))


if __name__ == "__main__":
    RangeBreakout().run()
