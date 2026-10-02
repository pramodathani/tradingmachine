"""Print `time_from` beside `time_at` for the same time, to show the one difference between them.

Both hold from the time onwards. A time already passed today makes UBI refuse `time_at` when the plan is placed, while `time_from` holds at once. The program prints both conditions for a morning time, with the rule each follows. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/time_from/time_from/time_from_beside_time_at.py
"""

import json

from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import time_at
from tradingmachine.orders.plan_parts import time_from


class TimeFromBesideTimeAt:
    """Two orders waiting for the same time of day, one by `time_at` and one by `time_from`.

    Attributes:
        time: The str time of day both orders wait for.
    """

    def __init__(self):
        """Sets the time of day.

        Raises:
            Nothing.
        """
        self.time = "09:20"

    def run(self) -> None:
        """Prints both orders' objects with the rule each follows.

        Returns:
            None.

        Raises:
            Nothing.
        """
        refused = order_part.OrderPart(trigger=time_at.TimeAt(self.time))
        started = order_part.OrderPart(trigger=time_from.TimeFrom(self.time))
        print(f"With time_at, a plan placed after {self.time} is refused:")
        print(json.dumps(refused.document(), indent=2))
        print(f"With time_from, a plan placed after {self.time} starts:")
        print(json.dumps(started.document(), indent=2))


if __name__ == "__main__":
    TimeFromBesideTimeAt().run()
