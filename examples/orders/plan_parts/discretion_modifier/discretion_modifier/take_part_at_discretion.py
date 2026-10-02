"""Build a limit sell at a fixed price that takes only part of its quantity when a bid comes within reach.

The program reads Vodafone Idea's last price and builds a sell of 100 shares resting 1% above it, with a discretion of a tenth of a rupee that takes 40 shares at a time, so the rest keeps its place at the visible price. It prints the order object UBI would read. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/discretion_modifier/discretion_modifier/take_part_at_discretion.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import discretion_modifier
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part


class PartialDiscretionSell:
    """A fixed-price sell of Vodafone Idea that takes part of its quantity at discretion.

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
        """Prints the visible price and the order's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        visible_price = round(last_price * 1.01, 2)
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="sell",
            quantity=100,
            pricing=fixed_pricing.FixedPricing(
                price=visible_price,
                order_type="LIMIT",
            ),
            discretion=discretion_modifier.DiscretionModifier(
                points=0.1,
                quantity=40,
            ),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(f"Visible sell price: {visible_price}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    PartialDiscretionSell().run()
