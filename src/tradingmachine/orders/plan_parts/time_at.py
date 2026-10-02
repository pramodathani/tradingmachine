"""The `time_at` trigger of a plan: a time of day reached on the instrument's next trading day.

UBI works the moment out once, when the plan is placed, so a time already passed on a trading day is refused, and a weekend or holiday rolls to the next trading day. It holds from that moment on, exactly as `time_after` does; the two names exist so a plan reads naturally.

Typical usage example:

  condition = time_at.TimeAt("10:00")
  document = condition.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class TimeAt(plan_part.PlanPart):
    """A condition that holds from a time of day onwards.

    Attributes:
        time: The str time of day, such as `10:00`.
    """

    def __init__(
        self,
        time: str,
    ):
        """Initialises the condition with its time of day.

        Args:
            time: The str time of day in India, such as `10:00` or `14:45`.

        Raises:
            Nothing.
        """
        self.time = time

    def document(self) -> dict:
        """Builds the `time_at` condition UBI reads.

        Returns:
            A dict with the single key `time_at`, whose value is the str time of day.

        Raises:
            Nothing.

        Examples:
            Print a condition that holds from ten in the morning:

            ```python
            from tradingmachine.orders.plan_parts import time_at

            print(time_at.TimeAt("10:00").document())
            ```

            Print an order held until a quarter to three in the afternoon:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import time_at

            part = order_part.OrderPart(trigger=time_at.TimeAt("14:45"))
            print(part.document())
            ```
        """
        return {
            "time_at": self.time,
        }
