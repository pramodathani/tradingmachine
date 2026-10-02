"""Build a fixed-price sell that is refused rather than sent if it would trade at once.

The program reads Vodafone Idea's last price and builds a limit sell half a percent above it, with a post-only guard left at UBI's default of `refuse`, so if the bid has risen to the price by the time the order is sent, the order ends as refused instead of trading. It prints the order object UBI would read. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/post_only_guard/post_only_guard/refuse_a_limit_that_would_cross.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import post_only_guard


class RefusedIfCrossing:
    """A post-only limit sell of Vodafone Idea above the last price.

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
        """Prints the limit and the order's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        limit_price = round(last_price * 1.005, 2)
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="sell",
            quantity=10,
            pricing=fixed_pricing.FixedPricing(
                price=limit_price,
                order_type="LIMIT",
            ),
            guard=post_only_guard.PostOnlyGuard(),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(f"Post-only sell limit: {limit_price}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    RefusedIfCrossing().run()
