"""Build a dip entry that ignores the first hour of trading.

A dip in the first hour is often the opening auction settling rather than a real move. The program joins a `time_after` condition at 10:15 with a fall to a level in an `AllConditions` group, so the entry counts the dip only after that time. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/time_after/time_after/ignore_dips_in_the_first_hour.py
"""

import json

from tradingmachine.orders.plan_parts import all_conditions
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses
from tradingmachine.orders.plan_parts import time_after


class LateDipEntry:
    """An entry that waits for a dip to 995 after 10:15.

    Attributes:
        dip_level: The float level in rupees the price must fall to.
        start_time: The str time of day from which the dip counts.
    """

    def __init__(self):
        """Sets the level and the time.

        Raises:
            Nothing.
        """
        self.dip_level = 995.0
        self.start_time = "10:15"

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
                    time_after.TimeAfter(self.start_time),
                    price_crosses.PriceCrosses(level=self.dip_level),
                ]
            ),
        )
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    LateDipEntry().run()
