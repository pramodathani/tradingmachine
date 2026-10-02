"""Build a breakout entry that counts only before eleven in the morning.

Many breakout traders trust a morning breakout and distrust one late in the day. The program joins a rise through 1010 with a `time_before` condition at 11:00 in an `AllConditions` group, so the entry fires only if the breakout happens in the morning. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/time_before/time_before/morning_only_breakout.py
"""

import json

from tradingmachine.orders.plan_parts import all_conditions
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses
from tradingmachine.orders.plan_parts import time_before


class MorningBreakout:
    """An entry on a rise through 1010 before 11:00.

    Attributes:
        breakout_level: The float level in rupees the price must rise to.
        end_time: The str time of day after which the breakout no longer counts.
    """

    def __init__(self):
        """Sets the level and the time.

        Raises:
            Nothing.
        """
        self.breakout_level = 1010.0
        self.end_time = "11:00"

    def run(self) -> None:
        """Prints the entry's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        part = order_part.OrderPart(
            trigger=all_conditions.AllConditions(
                [
                    price_crosses.PriceCrosses(
                        level=self.breakout_level,
                        direction="at_or_above",
                    ),
                    time_before.TimeBefore(self.end_time),
                ]
            ),
        )
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    MorningBreakout().run()
