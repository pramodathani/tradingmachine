"""The `daily` execution of a plan: the order sent again each trading morning, for an order the exchange ends at the close.

A native stop dies at the close, so a position held for a week needs a new one every morning. This sends the whole order each trading day at `arm_at`, `09:20` by default, after the pre-open has settled, and not on a day the instrument does not trade. A plan placed after that time on a trading day first sends on the next trading morning. Once anything has traded no more is sent, and since UBI's fix of 2026-10-02 a stop that has traded completes the order rather than being sent again the next morning.

It is one of only two executions a resting stop may have, the other being `AllAtOnceExecution`, because renewing a stop each day still protects the whole position at once while splitting it would not. Pair it with a `Lifetime` in `after_days`, which ends it and keeps the plan across days. It does not nest.

Typical usage example:

  execution = daily_execution.DailyExecution()
  part = order_part.OrderPart(execution=execution)
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class DailyExecution(plan_part.PlanPart):
    """An execution that sends the order again at a set time each trading day until anything trades.

    Attributes:
        arm_at: The str time of day in India, `HH:MM`, to send at, or None for UBI's default of `09:20`.
    """

    def __init__(
        self,
        *,
        arm_at: str | None = None,
    ):
        """Initialises the execution with the time it sends at.

        Args:
            arm_at: The str time of day in India, `HH:MM`, to send at each trading day, or None for UBI's default of `09:20`.

        Raises:
            Nothing.
        """
        self.arm_at = arm_at

    def document(self) -> dict:
        """Builds the `daily` execution object UBI reads.

        Returns:
            A dict with the single key `daily`, whose value holds `arm_at` when it is set and is otherwise empty.

        Raises:
            Nothing.

        Examples:
            Print the execution at UBI's default time of 09:20:

            ```python
            from tradingmachine.orders.plan_parts import daily_execution

            execution = daily_execution.DailyExecution()
            print(execution.document())
            ```

            Print a protective stop renewed at half past nine every trading morning:

            ```python
            from tradingmachine.orders.plan_parts import daily_execution
            from tradingmachine.orders.plan_parts import native_stop_pricing
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                side="protect",
                pricing=native_stop_pricing.NativeStopPricing(
                    trigger_price=950.0,
                    limit_price=948.0,
                ),
                execution=daily_execution.DailyExecution(arm_at="09:30"),
            )
            print(part.document())
            ```
        """
        settings = {}
        if self.arm_at is not None:
            settings["arm_at"] = self.arm_at
        return {
            "daily": settings,
        }
