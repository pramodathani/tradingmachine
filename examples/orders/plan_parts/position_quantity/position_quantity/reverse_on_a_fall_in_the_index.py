"""Build a stop-and-reverse on Vodafone Idea that fires when the Nifty 50 falls 1%.

The program reads the Nifty 50's level and builds a close of Vodafone Idea's intraday position, triggered by the index rather than the share, with `ratio` 2, so one order closes the position and opens the same size the other way. A long of 1,000 shares therefore becomes a short of 1,000. It prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/position_quantity/position_quantity/reverse_on_a_fall_in_the_index.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import position_quantity
from tradingmachine.orders.plan_parts import price_crosses


class ReverseOnIndexFall:
    """A close-and-reverse of a share, fired by the index.

    Attributes:
        share: The tradingmachine.assets.equities.Equity whose position is reversed.
        index: The tradingmachine.assets.equities.EquityIndex watched.
    """

    def __init__(self):
        """Looks the share and the index up.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share or the index could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")

    def run(self) -> None:
        """Prints the plan.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the index.
        """
        index_level = self.index.last_price
        if index_level is None:
            raise ValueError(f"UBI has no last price for {self.index!r}")
        plan = order_part.OrderPart(
            trigger=price_crosses.PriceCrosses(
                level=round(index_level * 0.99, 2),
                direction="at_or_below",
                instrument=self.index,
            ),
            side="close",
            quantity=position_quantity.PositionQuantity(
                product="intraday",
                held_instruments=[
                    self.share,
                ],
                ratio=2,
            ),
        )
        print(f"Nifty 50 at {index_level}")
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    ReverseOnIndexFall().run()
