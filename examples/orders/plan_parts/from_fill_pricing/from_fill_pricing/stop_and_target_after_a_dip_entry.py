"""Build a dip entry followed by a stop and a target measured from wherever the entry fills.

The program reads Vodafone Idea's last price and builds a Then join: a buy that waits for the price to fall 1%, and on each of its fills an Either join of a stop 2% of the price below the fill and a target 4% above it, which share the position so a fill on one reduces the other. The exits need no absolute prices, because UBI measures them from the entry's average fill. It prints the join's object as UBI would read it. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/from_fill_pricing/from_fill_pricing/stop_and_target_after_a_dip_entry.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import either_part
from tradingmachine.orders.plan_parts import from_fill_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses
from tradingmachine.orders.plan_parts import then_part


class DipEntryWithExits:
    """A dip buy of Vodafone Idea with a stop and a target measured from its fill.

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
        tick_size = 0.05
        if self.share.tick_size is not None:
            tick_size = float(self.share.tick_size)
        stop = order_part.OrderPart(
            side="protect",
            pricing=from_fill_pricing.FromFillPricing(
                stop_distance=round(last_price * 0.02, 2),
                stop_limit_offset=tick_size,
            ),
        )
        target = order_part.OrderPart(
            side="protect",
            pricing=from_fill_pricing.FromFillPricing(
                target_distance=round(last_price * 0.04, 2),
            ),
        )
        part = then_part.ThenPart(
            first=order_part.OrderPart(
                trigger=price_crosses.PriceCrosses(
                    level=round(last_price * 0.99, 2),
                ),
            ),
            each_fill=either_part.EitherPart(
                children=[
                    stop,
                    target,
                ],
                sibling_rule="reduce",
            ),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    DipEntryWithExits().run()
