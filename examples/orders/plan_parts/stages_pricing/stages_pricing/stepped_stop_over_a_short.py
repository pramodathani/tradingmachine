"""Build a stepped stop over a short position, whose gains are measured downwards from the entry.

The program reads Vodafone Idea's last price and builds a protecting stop for a position opened by a sale at that price: it starts 2% above, moves to breakeven once the price has fallen 2%, and to a 2% gain once it has fallen 4%, moving only in steps of two ticks. Because gains are measured in the position's favour, the same positive numbers serve a short as a long. It prints the order object UBI would read. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/stages_pricing/stages_pricing/stepped_stop_over_a_short.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import stage_rule
from tradingmachine.orders.plan_parts import stages_pricing


class ShortSteppedStop:
    """A stepped buy stop protecting a short position in Vodafone Idea.

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
        """Prints the protecting order's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        two_percent = round(last_price * 0.02, 2)
        stop = stages_pricing.StagesPricing(
            entry_price=last_price,
            stop_price=round(last_price + two_percent, 2),
            limit_offset=0.05,
            rules=[
                stage_rule.StageRule(gain=two_percent, stop_at_gain=0.0),
                stage_rule.StageRule(
                    gain=round(two_percent * 2, 2),
                    stop_at_gain=two_percent,
                ),
            ],
            step_ticks=2,
        )
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="buy",
            quantity=1,
            pricing=stop,
        )
        print(f"Short entered at {last_price}, stop starts above it:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    ShortSteppedStop().run()
