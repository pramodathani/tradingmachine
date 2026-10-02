"""Build an entry that waits until half past nine, when the opening rush has settled.

Prices in the first quarter of an hour are often wild, so the program holds an entry with a `time_at` condition until 09:30 on the instrument's next trading day, and prices it as a marketable limit so it fills as soon as it is sent. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/time_at/time_at/buy_once_the_opening_settles.py
"""

import json

from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import time_at


class SettledOpeningEntry:
    """An entry held until 09:30.

    Attributes:
        entry_time: The str time of day the entry is sent at.
    """

    def __init__(self):
        """Sets the entry time.

        Raises:
            Nothing.
        """
        self.entry_time = "09:30"

    def run(self) -> None:
        """Prints the entry's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        part = order_part.OrderPart(
            trigger=time_at.TimeAt(self.entry_time),
            pricing=marketable_pricing.MarketablePricing(),
        )
        print(f"The entry is held until {self.entry_time}:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    SettledOpeningEntry().run()
