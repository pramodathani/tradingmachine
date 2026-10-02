"""The `all_at_once` execution of a plan: the whole quantity sent as one broker order.

This is what UBI does when an order names no execution, so it is needed only to say so explicitly, or to replace an execution an earlier preset gave. Under a join that changes how much the order should trade, the one resting order is modified rather than another being sent, so a bracket's exits grow and shrink in place. It is one of the two executions a resting stop may have, the other being `DailyExecution`.

Typical usage example:

  execution = all_at_once_execution.AllAtOnceExecution()
  part = order_part.OrderPart(execution=execution)
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class AllAtOnceExecution(plan_part.PlanPart):
    """An execution that sends the order's whole quantity as one broker order, which is UBI's default."""

    def document(self) -> dict:
        """Builds the `all_at_once` execution object UBI reads.

        Returns:
            A dict with the single key `all_at_once`, whose value is an empty dict, because the execution takes no settings.

        Raises:
            Nothing.

        Examples:
            Print the execution on its own:

            ```python
            from tradingmachine.orders.plan_parts import all_at_once_execution

            execution = all_at_once_execution.AllAtOnceExecution()
            print(execution.document())
            ```

            Print a protective stop that is sent whole, which is the only way other than daily that a resting stop may be sent:

            ```python
            from tradingmachine.orders.plan_parts import all_at_once_execution
            from tradingmachine.orders.plan_parts import native_stop_pricing
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                side="protect",
                pricing=native_stop_pricing.NativeStopPricing(
                    trigger_price=990.0,
                    limit_price=989.0,
                ),
                execution=all_at_once_execution.AllAtOnceExecution(),
            )
            print(part.document())
            ```
        """
        return {
            "all_at_once": {},
        }
