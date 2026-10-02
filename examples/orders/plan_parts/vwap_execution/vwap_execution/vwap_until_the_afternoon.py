"""Build a VWAP sell of Vodafone Idea that runs from whenever it starts until three in the afternoon.

The program builds an order for 5000 shares sent as ten VWAP slices with `until` rather than `over_minutes`, so the slices are spread over whatever is left of the day up to 15:00, and sized by UBI's NSE equity volume profile counted from the 09:15 open. A second order does the same with each slice shown as an iceberg of 200, a nested execution. UBI refuses either if it starts after 15:00. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/vwap_execution/vwap_execution/vwap_until_the_afternoon.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import iceberg_execution
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import vwap_execution


class VwapUntilTheAfternoon:
    """Two VWAP sells of Vodafone Idea ending at 15:00, one plain and one of icebergs.

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
        """Prints both orders' objects.

        Returns:
            None.

        Raises:
            Nothing.
        """
        inner_executions = {
            "each slice sent whole": None,
            "each slice shown 200 at a time": iceberg_execution.IcebergExecution(
                visible_quantity=200,
            ),
        }
        for description, inner_execution in inner_executions.items():
            part = order_part.OrderPart(
                instrument=self.share,
                transaction_type="sell",
                quantity=5000,
                product="cnc",
                pricing=marketable_pricing.MarketablePricing(buffer_ticks=1),
                execution=vwap_execution.VwapExecution(
                    slices=10,
                    until="15:00",
                ),
                inner_execution=inner_execution,
            )
            print(f"A VWAP until 15:00, {description}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    VwapUntilTheAfternoon().run()
