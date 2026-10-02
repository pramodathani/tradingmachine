"""Build an entry whose profit target grows with every fill by new orders rather than by resizing one.

The program reads Vodafone Idea's last price and builds a then join: a limit buy of 10000 shares one percent below that price, followed under `each_fill` by a target limit sell three percent above it. The target uses `TopUpExecution`, so each fill sends a new order for the shares not yet covered and every order keeps its place in the queue, where the default execution would change one order's size. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/top_up_execution/top_up_execution/target_that_grows_with_each_fill.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part
from tradingmachine.orders.plan_parts import top_up_execution


class GrowingTarget:
    """A buy of Vodafone Idea whose target is topped up with each fill.

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
        """Prints the join's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        entry_price = round(last_price * 0.99, 2)
        target_price = round(last_price * 1.03, 2)
        join = then_part.ThenPart(
            first=order_part.OrderPart(
                instrument=self.share,
                transaction_type="buy",
                quantity=10000,
                product="cnc",
                pricing=fixed_pricing.FixedPricing(
                    price=entry_price,
                    order_type="LIMIT",
                ),
            ),
            each_fill=order_part.OrderPart(
                side="protect",
                pricing=fixed_pricing.FixedPricing(
                    price=target_price,
                    order_type="LIMIT",
                ),
                execution=top_up_execution.TopUpExecution(),
            ),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(join.document(), indent=2))


if __name__ == "__main__":
    GrowingTarget().run()
