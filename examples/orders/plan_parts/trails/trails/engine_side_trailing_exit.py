"""Build a trailing exit kept inside UBI's order engine, which sends a marketable limit when the price pulls back.

Unlike a `TrailPricing` stop, nothing rests at the broker: the engine watches the best price and, once the last price pulls back five rupees from it, sends a protecting order a few ticks past the other side of the book. The program builds that order as a then join behind an entry and prints it. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/trails/trails/engine_side_trailing_exit.py
"""

import json

from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part
from tradingmachine.orders.plan_parts import trails


class EngineTrailingExit:
    """An entry followed by an exit that fires on a five-rupee pullback.

    Attributes:
        pullback_points: The float pullback in rupees that fires the exit.
    """

    def __init__(self):
        """Sets the pullback distance.

        Raises:
            Nothing.
        """
        self.pullback_points = 5.0

    def build_plan(self) -> then_part.ThenPart:
        """Builds the entry and its trailing exit.

        Returns:
            The tradingmachine.orders.plan_parts.then_part.ThenPart.

        Raises:
            Nothing.
        """
        return then_part.ThenPart(
            first=order_part.OrderPart(),
            each_fill=order_part.OrderPart(
                side="protect",
                trigger=trails.Trails(points=self.pullback_points),
                pricing=marketable_pricing.MarketablePricing(buffer_ticks=3),
            ),
        )

    def run(self) -> None:
        """Prints the plan's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(json.dumps(self.build_plan().document(), indent=2))
        print("The exit does nothing while the order engine is down.")


if __name__ == "__main__":
    EngineTrailingExit().run()
