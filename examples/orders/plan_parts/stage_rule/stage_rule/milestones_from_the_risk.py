"""Build a table of stop milestones measured in multiples of a trade's risk, ending in a trail.

The program reads Vodafone Idea's last price, treats a stop 2% below it as the trade's risk, and builds three milestones: at one risk of gain the stop moves to breakeven, at two it locks in one risk, and at three it starts trailing one risk behind. It prints each milestone's entry and the list as UBI would read it in a `stages` rule. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/stage_rule/stage_rule/milestones_from_the_risk.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import stage_rule


class RiskMilestones:
    """Three stop milestones for Vodafone Idea, in multiples of a 2% risk.

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
        """Prints the risk and the milestones.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        risk = round(last_price * 0.02, 2)
        rules = [
            stage_rule.StageRule(gain=risk, stop_at_gain=0.0),
            stage_rule.StageRule(gain=round(risk * 2, 2), stop_at_gain=risk),
            stage_rule.StageRule(gain=round(risk * 3, 2), trail_points=risk),
        ]
        rule_documents = []
        for rule in rules:
            rule_documents.append(rule.document())
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(f"One risk, 2% of the price: {risk}")
        print(json.dumps(rule_documents, indent=2))


if __name__ == "__main__":
    RiskMilestones().run()
