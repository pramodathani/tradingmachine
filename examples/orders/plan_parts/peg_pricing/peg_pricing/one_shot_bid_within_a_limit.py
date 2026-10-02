"""Build a buy priced once at the bid and never above a limit worked out from the last price.

The program reads Vodafone Idea's last price and builds a plan order whose template is a limit buy 1% above it, with one order pegged to its own side of the book that does not follow it afterwards and treats the template's limit as the worst price it takes. This is how each purchase of UBI's accumulation type is priced. It prints the plan's synthetic object. The plan order is only built; nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/peg_pricing/peg_pricing/one_shot_bid_within_a_limit.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders import plan
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import peg_pricing


class OneShotBid:
    """A buy of Vodafone Idea priced once at the bid, within a limit.

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
        """Prints the limit and the plan's synthetic object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        limit_price = round(last_price * 1.01, 2)
        order = plan.PlanOrder(
            self.share,
            transaction_type="buy",
            product="mis",
            order_type="limit",
            quantity=1,
            price=limit_price,
            plan=order_part.OrderPart(
                pricing=peg_pricing.PegPricing(
                    reference="own_touch",
                    follows=False,
                    within_body_price=True,
                ),
            ),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(f"Template limit, the most the buy pays: {limit_price}")
        print(json.dumps(order.synthetic, indent=2))


if __name__ == "__main__":
    OneShotBid().run()
