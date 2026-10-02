"""Build a buy that rests on the bid and quietly reaches up to take an offer that comes close.

The program reads Vodafone Idea's tick size and builds a buy pegged to its own side of the book, with a discretion of two ticks, so when an offer appears within two ticks of the visible bid UBI takes it with everything still resting. It prints the order object UBI would read. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/discretion_modifier/discretion_modifier/hidden_reach_on_a_resting_bid.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import discretion_modifier
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import peg_pricing


class HiddenReachBid:
    """A resting buy of Vodafone Idea with two ticks of discretion.

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
        """Prints the discretion and the order's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        tick_size = 0.05
        if self.share.tick_size is not None:
            tick_size = float(self.share.tick_size)
        points = round(tick_size * 2, 2)
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="buy",
            quantity=10,
            pricing=peg_pricing.PegPricing(reference="own_touch"),
            discretion=discretion_modifier.DiscretionModifier(points=points),
        )
        print(f"Tick size of {self.share.symbol}: {tick_size}")
        print(f"Discretion, two ticks: {points}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    HiddenReachBid().run()
