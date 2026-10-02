"""Build a VWAP with a volume profile of its own, and show how its weights share out the slices.

UBI's default profile is the NSE equity day's shape and is used only for equity; a currency or commodity order with no profile of its own gets even slices. The program builds a VWAP over the first two hours of a session with its own profile, four half-hour weights heavy at the open, and prints the order and each half hour's share of the weight. The half hours count from the segment's own open, 09:15 for equity and 09:00 for currency and MCX. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/vwap_execution/vwap_execution/own_volume_profile.py
"""

import json

from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import vwap_execution


class OwnVolumeProfile:
    """A VWAP over two hours whose slices follow a profile given here.

    Attributes:
        execution: The tradingmachine.orders.plan_parts.vwap_execution.VwapExecution with its own profile.
        part: The tradingmachine.orders.plan_parts.order_part.OrderPart the program prints.
    """

    def __init__(self):
        """Builds the execution and the order.

        Raises:
            Nothing.
        """
        self.execution = vwap_execution.VwapExecution(
            slices=8,
            over_minutes=120,
            volume_profile=[
                4.0,
                2.5,
                2.0,
                1.5,
            ],
        )
        self.part = order_part.OrderPart(
            pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
            execution=self.execution,
        )

    def run(self) -> None:
        """Prints the order's object and each half hour's share of the profile.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(json.dumps(self.part.document(), indent=2))
        total = sum(self.execution.volume_profile)
        half_hour = 1
        for weight in self.execution.volume_profile:
            print(
                f"Half hour {half_hour} after the open: {weight / total:.0%} of the weight"
            )
            half_hour = half_hour + 1


if __name__ == "__main__":
    OwnVolumeProfile().run()
