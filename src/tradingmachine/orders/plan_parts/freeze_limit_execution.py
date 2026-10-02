"""The `freeze_limit` execution of a plan: an order above the exchange's freeze quantity split into orders each below it, all sent at once to one broker.

The broker is chosen first, because each broker publishes its freeze quantity in its own units: for one MCX silver option, brokers with a lot of 30 report 600 and brokers with a lot of 1 report 20, both meaning twenty lots. The order's quantity in that broker's terms is compared with that figure and split evenly into orders each within it, every one sent to that broker at once. A broker that publishes no freeze quantity gets the order whole, and an order needing more than 20 slices is refused.

It takes no settings, is what UBI's `freeze_slicer` preset uses, and does not nest, so an order above the freeze quantity that also wants slicing over time cannot be built. It cannot carry a resting stop.

Typical usage example:

  execution = freeze_limit_execution.FreezeLimitExecution()
  part = order_part.OrderPart(execution=execution)
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class FreezeLimitExecution(plan_part.PlanPart):
    """An execution that splits an order larger than the chosen broker's freeze quantity into equal orders sent together."""

    def document(self) -> dict:
        """Builds the `freeze_limit` execution object UBI reads.

        Returns:
            A dict with the single key `freeze_limit`, whose value is an empty dict, because the execution takes no settings.

        Raises:
            Nothing.

        Examples:
            Print the execution on its own:

            ```python
            from tradingmachine.orders.plan_parts import freeze_limit_execution

            execution = freeze_limit_execution.FreezeLimitExecution()
            print(execution.document())
            ```

            Print a large order of 9000 that takes what is offered, split below the freeze quantity:

            ```python
            from tradingmachine.orders.plan_parts import freeze_limit_execution
            from tradingmachine.orders.plan_parts import marketable_pricing
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                quantity=9000,
                pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
                execution=freeze_limit_execution.FreezeLimitExecution(),
            )
            print(part.document())
            ```
        """
        return {
            "freeze_limit": {},
        }
