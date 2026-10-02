"""Build a buy pegged to the midpoint that never pays more than a ceiling worked out from the last price.

The program reads Vodafone Idea's last price and builds a buy that follows the midpoint of the book, with a cap half a percent above the last price, so a rising market leaves the order at the cap rather than dragging it up. It prints the order object UBI would read. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/cap_modifier/cap_modifier/peg_with_a_ceiling.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import cap_modifier
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import peg_pricing


class CappedMidpointBuy:
    """A buy of Vodafone Idea pegged to the midpoint, capped above the last price.

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
        """Prints the ceiling and the order's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        ceiling_price = round(last_price * 1.005, 2)
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="buy",
            quantity=1,
            pricing=peg_pricing.PegPricing(reference="mid"),
            cap=cap_modifier.CapModifier(worst_price=ceiling_price),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(f"Most the buy pays: {ceiling_price}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    CappedMidpointBuy().run()
