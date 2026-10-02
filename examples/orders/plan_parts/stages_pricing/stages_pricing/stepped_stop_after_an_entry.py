"""Build an entry followed by a stepped stop that moves to breakeven and then trails.

The program reads Vodafone Idea's last price and builds a Then join: a buy, and on each of its fills a protecting stop 3% below the last price that moves to breakeven at a 3% gain and trails 2% behind from a 6% gain. It prints the join's object as UBI would read it. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/stages_pricing/stages_pricing/stepped_stop_after_an_entry.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import stage_rule
from tradingmachine.orders.plan_parts import stages_pricing
from tradingmachine.orders.plan_parts import then_part


class SteppedStopAfterEntry:
    """A buy of Vodafone Idea protected by a stepped stop.

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
        three_percent = round(last_price * 0.03, 2)
        stop = stages_pricing.StagesPricing(
            entry_price=last_price,
            stop_price=round(last_price - three_percent, 2),
            limit_offset=tick_size,
            rules=[
                stage_rule.StageRule(gain=three_percent, stop_at_gain=0.0),
                stage_rule.StageRule(
                    gain=round(three_percent * 2, 2),
                    trail_points=round(last_price * 0.02, 2),
                ),
            ],
        )
        part = then_part.ThenPart(
            first=order_part.OrderPart(),
            each_fill=order_part.OrderPart(side="protect", pricing=stop),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    SteppedStopAfterEntry().run()
