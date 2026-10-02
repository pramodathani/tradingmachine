"""Build a trailing stop for a share sized from its price, in rupees and as a percentage, with a step that limits modifications.

The program reads Vodafone Idea's last price and builds two `TrailPricing` rules 2% behind the market, one in rupees and one as a percentage, the second moving only in steps of three ticks so the broker sees fewer modifications. It prints both on a protecting order. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/trail_pricing/trail_pricing/trailing_stop_from_the_share_price.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import trail_pricing


class ShareTrailingStop:
    """Two trailing stops for Vodafone Idea, 2% behind the market.

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
        """Prints both protecting orders' objects.

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
        points = round(last_price * 0.02, 2)
        rules = {
            "in rupees": trail_pricing.TrailPricing(
                points=points,
                limit_offset=tick_size,
            ),
            "as a percentage, in steps of three ticks": trail_pricing.TrailPricing(
                percent=2.0,
                limit_offset=tick_size,
                step_ticks=3,
            ),
        }
        print(f"Last price of {self.share.symbol}: {last_price}")
        for description, rule in rules.items():
            part = order_part.OrderPart(side="protect", pricing=rule)
            print(f"Trailing {description}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    ShareTrailingStop().run()
