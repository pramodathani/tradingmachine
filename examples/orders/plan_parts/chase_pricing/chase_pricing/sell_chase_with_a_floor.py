"""Build a sell that chases the bid but never sells below a floor worked out from the last price.

The program reads Vodafone Idea's last price and builds a sell that steps down a tick every five seconds from its own side of the book, with a cap 1% below the last price that every step respects. It prints the order object UBI would read. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/chase_pricing/chase_pricing/sell_chase_with_a_floor.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import cap_modifier
from tradingmachine.orders.plan_parts import chase_pricing
from tradingmachine.orders.plan_parts import order_part


class FlooredSellChase:
    """A chasing sell of Vodafone Idea that never goes below 1% under the last price.

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
        """Prints the floor and the order's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        floor_price = round(last_price * 0.99, 2)
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="sell",
            quantity=1,
            pricing=chase_pricing.ChasePricing(step_ticks=1, step_seconds=5),
            cap=cap_modifier.CapModifier(worst_price=floor_price),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(f"Least the sell takes: {floor_price}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    FlooredSellChase().run()
