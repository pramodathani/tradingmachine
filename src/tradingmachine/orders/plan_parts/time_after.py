"""The `time_after` trigger of a plan: from a time of day onwards on the instrument's next trading day.

It holds exactly as `time_at` does, and reads better inside `AllConditions`, where it keeps another condition to the part of the day after the time.

Typical usage example:

  condition = time_after.TimeAfter("09:30")
  document = condition.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class TimeAfter(plan_part.PlanPart):
    """A condition that holds from a time of day onwards.

    Attributes:
        time: The str time of day, such as `09:30`.
    """

    def __init__(
        self,
        time: str,
    ):
        """Initialises the condition with its time of day.

        Args:
            time: The str time of day in India, such as `09:30`.

        Raises:
            Nothing.
        """
        self.time = time

    def document(self) -> dict:
        """Builds the `time_after` condition UBI reads.

        Returns:
            A dict with the single key `time_after`, whose value is the str time of day.

        Raises:
            Nothing.

        Examples:
            Print a condition that holds from half past nine:

            ```python
            from tradingmachine.orders.plan_parts import time_after

            print(time_after.TimeAfter("09:30").document())
            ```

            Print a touch at 995 that counts only after the first quarter of an hour:

            ```python
            from tradingmachine.orders.plan_parts import all_conditions
            from tradingmachine.orders.plan_parts import price_crosses
            from tradingmachine.orders.plan_parts import time_after

            condition = all_conditions.AllConditions(
                [
                    time_after.TimeAfter("09:30"),
                    price_crosses.PriceCrosses(level=995.0),
                ]
            )
            print(condition.document())
            ```
        """
        return {
            "time_after": self.time,
        }
