"""Build buys that chase the offer at three different paces, the last one crossing the book after a minute.

The program builds three chasing buys of Vodafone Idea: one with UBI's defaults of a tick every five seconds, one that steps two ticks every ten seconds, and one that walks a tick every three seconds and moves to the offer once a minute has passed. It prints the order object UBI would read for each. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/chase_pricing/chase_pricing/walk_to_the_offer_then_cross.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import chase_pricing
from tradingmachine.orders.plan_parts import order_part


class ChasePaces:
    """Three chasing buys of Vodafone Idea at different paces.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
    """

    def __init__(self):
        """Looks up the share.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def run(self) -> None:
        """Prints the three orders' objects.

        Returns:
            None.

        Raises:
            Nothing.
        """
        rules = {
            "with UBI's defaults": chase_pricing.ChasePricing(),
            "two ticks every ten seconds": chase_pricing.ChasePricing(
                step_ticks=2,
                step_seconds=10,
            ),
            "a tick every three seconds, crossing after a minute": (
                chase_pricing.ChasePricing(
                    step_ticks=1,
                    step_seconds=3,
                    cross_after_seconds=60,
                )
            ),
        }
        for description, rule in rules.items():
            part = order_part.OrderPart(
                instrument=self.share,
                transaction_type="buy",
                quantity=1,
                pricing=rule,
            )
            print(f"Chasing buy of {self.share.symbol}, {description}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    ChasePaces().run()
