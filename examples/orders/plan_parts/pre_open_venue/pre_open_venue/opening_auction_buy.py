"""Build a buy of Vodafone Idea sent into the pre-open session at two minutes past nine, so it trades at the opening auction's price.

The program reads the share's last price and builds a limit buy 1% above it, which the auction fills at its single opening price if that price is at or below the limit. The order takes no trigger, because UBI sends it at the venue's `at_time` through a trigger of its own, and it is a `LIMIT` order, one of the two order types the pre-open takes. It prints the plan, and the venue entry alone at UBI's default time of 09:00:30. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/pre_open_venue/pre_open_venue/opening_auction_buy.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import pre_open_venue


class OpeningAuctionBuy:
    """A limit buy sent into the pre-open session.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
    """

    def __init__(self):
        """Looks the share up.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def run(self) -> None:
        """Prints the plan and the default venue entry.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        plan = order_part.OrderPart(
            quantity=1000,
            product="cnc",
            pricing=fixed_pricing.FixedPricing(
                price=round(last_price * 1.01, 2),
                order_type="LIMIT",
            ),
            venue=pre_open_venue.PreOpenVenue(at_time="09:02"),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(plan.document(), indent=2))
        print("The venue at UBI's default time:")
        print(json.dumps(pre_open_venue.PreOpenVenue().document(), indent=2))


if __name__ == "__main__":
    OpeningAuctionBuy().run()
