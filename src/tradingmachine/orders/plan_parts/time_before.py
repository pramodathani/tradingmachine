"""The `time_before` trigger of a plan: until a time of day on the instrument's next trading day.

On its own it holds at once, so it is meant for `AllConditions`, where it keeps another condition to the part of the day before the time.

Typical usage example:

  condition = time_before.TimeBefore("15:00")
  document = condition.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class TimeBefore(plan_part.PlanPart):
    """A condition that holds until a time of day.

    Attributes:
        time: The str time of day, such as `15:00`.
    """

    def __init__(
        self,
        time: str,
    ):
        """Initialises the condition with its time of day.

        Args:
            time: The str time of day in India, such as `15:00`.

        Raises:
            Nothing.
        """
        self.time = time

    def document(self) -> dict:
        """Builds the `time_before` condition UBI reads.

        Returns:
            A dict with the single key `time_before`, whose value is the str time of day.

        Raises:
            Nothing.

        Examples:
            Print a condition that holds until three in the afternoon:

            ```python
            from tradingmachine.orders.plan_parts import time_before

            print(time_before.TimeBefore("15:00").document())
            ```

            Print a touch at 995 that counts only between ten and three:

            ```python
            from tradingmachine.orders.plan_parts import all_conditions
            from tradingmachine.orders.plan_parts import price_crosses
            from tradingmachine.orders.plan_parts import time_after
            from tradingmachine.orders.plan_parts import time_before

            condition = all_conditions.AllConditions(
                [
                    time_after.TimeAfter("10:00"),
                    time_before.TimeBefore("15:00"),
                    price_crosses.PriceCrosses(level=995.0),
                ]
            )
            print(condition.document())
            ```
        """
        return {
            "time_before": self.time,
        }
