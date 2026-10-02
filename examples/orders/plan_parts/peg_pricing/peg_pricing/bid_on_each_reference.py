"""Build a buy of a share pegged to each of the three places in the book a peg can follow.

The program looks up Vodafone Idea and builds three orders, one pegged to its own side of the book, one to the midpoint a tick further from filling, and one to the other side's touch, which fills at once. It prints the order object UBI would read for each. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/peg_pricing/peg_pricing/bid_on_each_reference.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import peg_pricing


class PegReferences:
    """Three pegged buys of Vodafone Idea, one for each reference.

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
            "on the bid": peg_pricing.PegPricing(reference="own_touch"),
            "a tick below the midpoint": peg_pricing.PegPricing(
                reference="mid",
                offset_ticks=1,
            ),
            "on the offer, filling at once": peg_pricing.PegPricing(
                reference="opposite_touch",
            ),
        }
        for description, rule in rules.items():
            part = order_part.OrderPart(
                instrument=self.share,
                transaction_type="buy",
                quantity=1,
                pricing=rule,
            )
            print(f"Buy of {self.share.symbol} pegged {description}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    PegReferences().run()
