"""Print one order ended each of the three ways UBI offers when its time comes.

A limit entry can be cancelled at 14:30, made marketable at 14:30 so it fills, or have whatever filled closed at market thirty minutes after placing. The program builds the same limit entry at 995 with each lifetime and prints all three. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/lifetime/lifetime/three_ways_to_end_an_order.py
"""

import json

from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import lifetime
from tradingmachine.orders.plan_parts import order_part


class ThreeEndings:
    """The same limit entry with three different lifetimes.

    Attributes:
        lifetimes: The dict of lifetime.Lifetime objects by the str name of how each ends.
    """

    def __init__(self):
        """Builds the three lifetimes.

        Raises:
            Nothing.
        """
        self.lifetimes = {
            "cancel at 14:30": lifetime.Lifetime(at_time="14:30"),
            "marketable at 14:30": lifetime.Lifetime(
                at_time="14:30",
                on_end="marketable",
            ),
            "close what filled after 30 minutes": lifetime.Lifetime(
                after_minutes=30,
                on_end="close_filled",
            ),
        }

    def run(self) -> None:
        """Prints the entry's object with each lifetime.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for name, ending in self.lifetimes.items():
            part = order_part.OrderPart(
                pricing=fixed_pricing.FixedPricing(price=995.0),
                lifetime=ending,
            )
            print(f"Ending by {name}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    ThreeEndings().run()
