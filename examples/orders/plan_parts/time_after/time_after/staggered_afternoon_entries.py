"""Build three entries that start at noon, one o'clock and two o'clock, to spread a purchase over the afternoon.

Each entry is its own order held by a `time_after` condition, so a position can be built in three parts without watching the clock. The program prints each entry's object. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/time_after/time_after/staggered_afternoon_entries.py
"""

import json

from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import time_after


class StaggeredEntries:
    """Three entries held until successive hours of the afternoon.

    Attributes:
        start_times: The list of str times of day the entries start at.
    """

    def __init__(self):
        """Sets the start times.

        Raises:
            Nothing.
        """
        self.start_times = [
            "12:00",
            "13:00",
            "14:00",
        ]

    def run(self) -> None:
        """Prints each entry's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for start_time in self.start_times:
            part = order_part.OrderPart(trigger=time_after.TimeAfter(start_time))
            print(f"Entry from {start_time}: {json.dumps(part.document())}")


if __name__ == "__main__":
    StaggeredEntries().run()
