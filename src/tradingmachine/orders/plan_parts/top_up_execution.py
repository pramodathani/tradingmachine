"""The `top_up` execution of a plan: a new broker order for whatever a join's growing target is missing, never a resized one.

It is meant for an order sized by a join, such as the second order of a `ThenPart` under `each_fill` that grows with every fill of the first. Each time the target grows, including after earlier orders have filled, one new broker order is sent for the quantity neither traded nor resting, so every broker order keeps the price it was given and its place in the queue; this is how UBI's `attached_hedge` and `legged_spread` presets grow their second leg. A target that shrinks cuts resting orders, newest first. A cancelled or rejected order stops it until the target next grows, so an `IOC` order the exchange cancels is not sent again at once, and a rejection stops it for good. A caller's change to the quantity of one of its orders is kept rather than modified back.

It takes no settings and does not nest.

Typical usage example:

  execution = top_up_execution.TopUpExecution()
  part = order_part.OrderPart(execution=execution)
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class TopUpExecution(plan_part.PlanPart):
    """An execution that sends one new broker order each time a join raises the order's target."""

    def document(self) -> dict:
        """Builds the `top_up` execution object UBI reads.

        Returns:
            A dict with the single key `top_up`, whose value is an empty dict, because the execution takes no settings.

        Raises:
            Nothing.

        Examples:
            Print the execution on its own:

            ```python
            from tradingmachine.orders.plan_parts import top_up_execution

            execution = top_up_execution.TopUpExecution()
            print(execution.document())
            ```

            Print an entry followed by an exit that grows with each fill, a new order being sent for every addition rather than the resting one being resized:

            ```python
            from tradingmachine.orders.plan_parts import fixed_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import then_part
            from tradingmachine.orders.plan_parts import top_up_execution

            plan = then_part.ThenPart(
                first=order_part.OrderPart(),
                each_fill=order_part.OrderPart(
                    side="protect",
                    pricing=fixed_pricing.FixedPricing(
                        price=1020.0,
                        order_type="LIMIT",
                    ),
                    execution=top_up_execution.TopUpExecution(),
                ),
            )
            print(plan.document())
            ```
        """
        return {
            "top_up": {},
        }
