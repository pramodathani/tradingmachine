"""Build a participation order whose every slice is itself spread out as a short TWAP.

The program builds an order for 3000 shares of Vodafone Idea that takes a tenth of the traded volume, at most twenty slices, and works each slice as a TWAP of three pieces over three minutes, so a burst of volume does not send one large order at once. This is a nested execution: `ParticipationExecution` is the outer one and `TwapExecution` the inner one. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/twap_execution/twap_execution/twap_inside_a_participation.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import participation_execution
from tradingmachine.orders.plan_parts import twap_execution


class ParticipationOfTwaps:
    """A buy of Vodafone Idea that follows the volume, each slice worked as a TWAP.

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
        """Prints the order's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="buy",
            quantity=3000,
            product="mis",
            pricing=marketable_pricing.MarketablePricing(buffer_ticks=1),
            execution=participation_execution.ParticipationExecution(
                percent=10.0,
                most_slices=20,
            ),
            inner_execution=twap_execution.TwapExecution(
                slices=3,
                over_minutes=3,
            ),
        )
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    ParticipationOfTwaps().run()
