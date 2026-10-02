"""Build an intraday trade that closes itself at ten past three, before the broker squares it off.

Brokers close intraday positions themselves shortly before the market shuts, often at a poor price. The program builds a then join whose child protects each fill of the entry with a market order held by a `time_at` condition until 15:10, so the position is closed on the trader's own terms. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/time_at/time_at/exit_before_the_intraday_square_off.py
"""

import json

from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part
from tradingmachine.orders.plan_parts import time_at


class TimedIntradayExit:
    """An entry whose every fill is closed at market at 15:10.

    Attributes:
        exit_time: The str time of day the exit is sent at.
    """

    def __init__(self):
        """Sets the exit time.

        Raises:
            Nothing.
        """
        self.exit_time = "15:10"

    def build_plan(self) -> then_part.ThenPart:
        """Builds the entry and its timed exit.

        Returns:
            The tradingmachine.orders.plan_parts.then_part.ThenPart.

        Raises:
            Nothing.
        """
        return then_part.ThenPart(
            first=order_part.OrderPart(),
            each_fill=order_part.OrderPart(
                side="protect",
                trigger=time_at.TimeAt(self.exit_time),
                pricing=fixed_pricing.FixedPricing(order_type="MARKET"),
            ),
        )

    def run(self) -> None:
        """Prints the plan's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(json.dumps(self.build_plan().document(), indent=2))


if __name__ == "__main__":
    TimedIntradayExit().run()
