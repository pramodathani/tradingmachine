"""Build trigger groups for three trading windows of the day, each a start time and an end time.

A `time_before` condition on its own holds at once, so it is paired with a `time_after` condition to make a window. The program builds the morning, midday and afternoon windows and prints each group's object, ready to be joined with a price condition. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/time_before/time_before/trading_windows.py
"""

import json

from tradingmachine.orders.plan_parts import all_conditions
from tradingmachine.orders.plan_parts import time_after
from tradingmachine.orders.plan_parts import time_before


class TradingWindows:
    """Three windows of the trading day.

    Attributes:
        windows: The dict of a str window name to a tuple (start, end) of str times of day.
    """

    def __init__(self):
        """Sets the windows.

        Raises:
            Nothing.
        """
        self.windows = {
            "morning": (
                "09:30",
                "11:00",
            ),
            "midday": (
                "11:00",
                "13:30",
            ),
            "afternoon": (
                "13:30",
                "15:00",
            ),
        }

    def window(self, start: str, end: str) -> all_conditions.AllConditions:
        """Builds the group that holds between two times.

        Args:
            start: The str time of day the window opens.
            end: The str time of day the window closes.

        Returns:
            The tradingmachine.orders.plan_parts.all_conditions.AllConditions.

        Raises:
            Nothing.
        """
        return all_conditions.AllConditions(
            [
                time_after.TimeAfter(start),
                time_before.TimeBefore(end),
            ]
        )

    def run(self) -> None:
        """Prints each window's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for name, times in self.windows.items():
            start, end = times
            print(f"{name}: {json.dumps(self.window(start, end).document())}")


if __name__ == "__main__":
    TradingWindows().run()
