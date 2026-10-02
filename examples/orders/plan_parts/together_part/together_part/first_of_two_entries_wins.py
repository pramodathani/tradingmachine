"""Build two entries into Vodafone Idea, one on a dip and one on a breakout, where the first to be done cancels the other.

The program reads the share's last price and builds a buy that waits for a 2% dip and a buy that waits for a 2% rise. They are joined with `done_when` set to `any`, so once one entry is done the other is cancelled, and with `group_margin` turned off, because only one of them will ever trade. It prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/together_part/together_part/first_of_two_entries_wins.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses
from tradingmachine.orders.plan_parts import together_part


class FirstEntryWins:
    """A dip entry and a breakout entry where whichever finishes first ends the other.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        move_fraction: The float fraction of the last price either entry waits for.
    """

    def __init__(self):
        """Looks the share up.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.move_fraction = 0.02

    def run(self) -> None:
        """Prints the plan.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        dip_level = round(last_price * (1 - self.move_fraction), 2)
        breakout_level = round(last_price * (1 + self.move_fraction), 2)
        plan = together_part.TogetherPart(
            children=[
                order_part.OrderPart(
                    trigger=price_crosses.PriceCrosses(
                        level=dip_level,
                        direction="at_or_below",
                    ),
                    pricing=marketable_pricing.MarketablePricing(),
                ),
                order_part.OrderPart(
                    trigger=price_crosses.PriceCrosses(
                        level=breakout_level,
                        direction="at_or_above",
                    ),
                    pricing=marketable_pricing.MarketablePricing(),
                ),
            ],
            group_margin=False,
            done_when="any",
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    FirstEntryWins().run()
