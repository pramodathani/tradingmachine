"""Build a buy of Vodafone Idea that is hedged by selling Yes Bank, half as many shares as each fill of the buy.

The hedge is a `then` join's child, which a `parent_fill` quantity must be. Every time the buy fills more, UBI resizes the hedge to half of what has filled in all, so a buy that fills 600 and then 400 more ends with a hedge of 500. It prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/parent_fill_quantity/parent_fill_quantity/hedge_half_of_each_fill.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import parent_fill_quantity
from tradingmachine.orders.plan_parts import then_part


class HalfHedgedBuy:
    """A buy in one share and a hedge in another sized to half its fills.

    Attributes:
        hedge_share: The tradingmachine.assets.equities.Equity sold as the hedge.
        hedge_ratio: The float share of each fill the hedge sells.
    """

    def __init__(self):
        """Looks the hedge share up.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.hedge_share = equities.Equity(exchange="nse", symbol="YESBANK")
        self.hedge_ratio = 0.5

    def run(self) -> None:
        """Prints the plan.

        Returns:
            None.

        Raises:
            Nothing.
        """
        plan = then_part.ThenPart(
            first=order_part.OrderPart(
                pricing=marketable_pricing.MarketablePricing(),
            ),
            each_fill=order_part.OrderPart(
                instrument=self.hedge_share,
                transaction_type="sell",
                product="mis",
                pricing=marketable_pricing.MarketablePricing(),
                quantity=parent_fill_quantity.ParentFillQuantity(
                    ratio=self.hedge_ratio,
                ),
            ),
        )
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    HalfHedgedBuy().run()
