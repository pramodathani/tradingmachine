"""Build a scale-in: three buys of Vodafone Idea at successively lower levels, each considered only once the one before is done.

The program reads the share's last price and builds three buys waiting for dips of 1%, 2% and 3%. In a sequence join the second buy does not start watching until the first is done, so a single sharp fall fills one buy at a time rather than all three at once. It prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/sequence_part/sequence_part/scale_in_on_three_dips.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses
from tradingmachine.orders.plan_parts import sequence_part


class ThreeStepScaleIn:
    """Three dip buys run one after another.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        dip_percents: The list of float percentages below the last price each buy waits for.
    """

    def __init__(self):
        """Looks the share up and sets the dips.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.dip_percents = [
            1.0,
            2.0,
            3.0,
        ]

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
        buys = []
        for dip_percent in self.dip_percents:
            level = round(last_price * (1 - dip_percent / 100), 2)
            buys.append(
                order_part.OrderPart(
                    trigger=price_crosses.PriceCrosses(level=level),
                    pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
                    quantity=500,
                ),
            )
        plan = sequence_part.SequencePart(children=buys)
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    ThreeStepScaleIn().run()
