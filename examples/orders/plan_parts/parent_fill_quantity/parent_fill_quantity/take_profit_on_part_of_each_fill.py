"""Build a buy of Vodafone Idea whose profit target sells only a third of what fills, leaving the rest to run.

The program reads the share's last price and follows the buy with a protecting limit 4% above it, sized by a `parent_fill` quantity with ratio one third rather than to the whole fill. It prints the plan, and then the same quantity with `whole_lots` on, which would round each size to whole lots of the instrument; for a share a lot is one share, so the rounding matters for futures and options. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/parent_fill_quantity/parent_fill_quantity/take_profit_on_part_of_each_fill.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import parent_fill_quantity
from tradingmachine.orders.plan_parts import then_part


class PartialTakeProfit:
    """A buy whose target takes a third of each fill off.

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
        """Prints the plan and the rounded quantity.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        plan = then_part.ThenPart(
            first=order_part.OrderPart(),
            each_fill=order_part.OrderPart(
                side="protect",
                pricing=fixed_pricing.FixedPricing(
                    price=round(last_price * 1.04, 2),
                    order_type="LIMIT",
                ),
                quantity=parent_fill_quantity.ParentFillQuantity(ratio=0.33),
            ),
        )
        rounded = parent_fill_quantity.ParentFillQuantity(
            ratio=0.33,
            whole_lots=True,
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(plan.document(), indent=2))
        print("The same quantity rounded to whole lots:")
        print(json.dumps(rounded.document(), indent=2))


if __name__ == "__main__":
    PartialTakeProfit().run()
