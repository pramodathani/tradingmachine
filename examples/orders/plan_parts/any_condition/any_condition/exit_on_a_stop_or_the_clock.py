"""Build an exit that fires on a fall to a stop level or at ten past three, whichever comes first.

A day trade should end either when it goes wrong or when the day ends. The program puts a fall to 990 and a `time_at` condition at 15:10 in an `AnyCondition` group on a protecting market order, and builds it behind an entry as a then join. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/any_condition/any_condition/exit_on_a_stop_or_the_clock.py
"""

import json

from tradingmachine.orders.plan_parts import any_condition
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses
from tradingmachine.orders.plan_parts import then_part
from tradingmachine.orders.plan_parts import time_at


class StopOrClockExit:
    """An entry whose exit fires on a stop level or at 15:10.

    Attributes:
        stop_level: The float level in rupees that fires the exit.
        exit_time: The str time of day that fires the exit.
    """

    def __init__(self):
        """Sets the level and the time.

        Raises:
            Nothing.
        """
        self.stop_level = 990.0
        self.exit_time = "15:10"

    def run(self) -> None:
        """Prints the plan's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        plan = then_part.ThenPart(
            first=order_part.OrderPart(),
            each_fill=order_part.OrderPart(
                side="protect",
                trigger=any_condition.AnyCondition(
                    [
                        price_crosses.PriceCrosses(
                            level=self.stop_level,
                            direction="at_or_below",
                        ),
                        time_at.TimeAt(self.exit_time),
                    ]
                ),
                pricing=fixed_pricing.FixedPricing(order_type="MARKET"),
            ),
        )
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    StopOrClockExit().run()
