"""Build a buy that follows the bid and is held on its own side rather than ever allowed to cross.

The program builds a buy of Vodafone Idea pegged to its own side of the book with a post-only guard set to `rest`, so a move that would cross the offer is held at the bid instead. It prints the order object UBI would read. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/post_only_guard/post_only_guard/maker_bid_that_rests.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import peg_pricing
from tradingmachine.orders.plan_parts import post_only_guard


class RestingMakerBid:
    """A pegged buy of Vodafone Idea that only ever rests.

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
        """Prints the order's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="buy",
            quantity=10,
            pricing=peg_pricing.PegPricing(reference="own_touch"),
            guard=post_only_guard.PostOnlyGuard(on_crossing="rest"),
        )
        print(f"Post-only buy of {self.share.symbol} on the bid:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    RestingMakerBid().run()
