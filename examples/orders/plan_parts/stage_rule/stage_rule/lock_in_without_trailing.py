"""Build a stepped stop whose milestones only lock in gains and never hand over to a trail.

The program builds four milestones for a stop on Vodafone Idea, each a quarter of a rupee further up, that move the stop to a smaller loss, to breakeven and then to two gains, and puts them on a protecting order's `stages` pricing. It prints the order object UBI would read. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/stage_rule/stage_rule/lock_in_without_trailing.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import stage_rule
from tradingmachine.orders.plan_parts import stages_pricing


class LockInStops:
    """A stepped stop for Vodafone Idea that locks in gains without trailing.

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
        entry_price = round(last_price, 2)
        stop_price = round(last_price - 0.5, 2)
        rules = [
            stage_rule.StageRule(gain=0.25, stop_at_gain=-0.25),
            stage_rule.StageRule(gain=0.5, stop_at_gain=0.0),
            stage_rule.StageRule(gain=0.75, stop_at_gain=0.25),
            stage_rule.StageRule(gain=1.0, stop_at_gain=0.5),
        ]
        part = order_part.OrderPart(
            side="protect",
            pricing=stages_pricing.StagesPricing(
                entry_price=entry_price,
                stop_price=stop_price,
                limit_offset=0.05,
                rules=rules,
            ),
        )
        print(f"Entry at {entry_price}, first stop at {stop_price}:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    LockInStops().run()
