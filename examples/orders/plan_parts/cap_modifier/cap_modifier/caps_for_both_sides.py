"""Build a capped buy and a capped sell, to show that a cap is the most a buy pays and the least a sell takes.

The program reads Vodafone Idea's last price and builds two chasing orders, a buy capped 1% above the last price and a sell capped 1% below it, so the same modifier is a ceiling on one side and a floor on the other. It prints the order object UBI would read for each. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/cap_modifier/cap_modifier/caps_for_both_sides.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import cap_modifier
from tradingmachine.orders.plan_parts import chase_pricing
from tradingmachine.orders.plan_parts import order_part


class CapsForBothSides:
    """A capped chasing buy and a capped chasing sell of Vodafone Idea.

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
        """Prints both orders' objects.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        worst_prices = {
            "buy": round(last_price * 1.01, 2),
            "sell": round(last_price * 0.99, 2),
        }
        print(f"Last price of {self.share.symbol}: {last_price}")
        for side, worst_price in worst_prices.items():
            part = order_part.OrderPart(
                instrument=self.share,
                transaction_type=side,
                quantity=1,
                pricing=chase_pricing.ChasePricing(),
                cap=cap_modifier.CapModifier(worst_price=worst_price),
            )
            print(f"Chasing {side} capped at {worst_price}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    CapsForBothSides().run()
