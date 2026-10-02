"""The `time_from` trigger of a plan: from a time of day onwards, starting at once when that time has already passed today.

It differs from `time_at` and `time_after` only in what happens to a time already passed on a trading day. Those two refuse such a time when the plan is placed, while `time_from` holds at once, so an order placed inside its window starts straight away rather than being refused. A time not yet reached today, or any time on a weekend or holiday, waits for that time on the instrument's next trading day, as `time_at` does.

Typical usage example:

  condition = time_from.TimeFrom("15:00")
  document = condition.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class TimeFrom(plan_part.PlanPart):
    """A condition that holds from a time of day onwards, and at once when that time has already passed today.

    Attributes:
        time: The str time of day, such as `15:00`.
    """

    def __init__(
        self,
        time: str,
    ):
        """Initialises the condition with its time of day.

        Args:
            time: The str time of day in India, such as `15:00` or `09:20:30`.

        Raises:
            Nothing.
        """
        self.time = time

    def document(self) -> dict:
        """Builds the `time_from` condition UBI reads.

        Returns:
            A dict with the single key `time_from`, whose value is the str time of day.

        Raises:
            Nothing.

        Examples:
            Print a condition that holds from three in the afternoon, or at once when placed after it:

            ```python
            from tradingmachine.orders.plan_parts import time_from

            print(time_from.TimeFrom("15:00").document())
            ```

            Print an order that is sent from twenty past nine, even when the plan is placed later in the morning:

            ```python
            from tradingmachine.orders.plan_parts import marketable_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import time_from

            part = order_part.OrderPart(
                trigger=time_from.TimeFrom("09:20"),
                pricing=marketable_pricing.MarketablePricing(),
            )
            print(part.document())
            ```
        """
        return {
            "time_from": self.time,
        }
