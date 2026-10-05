"""The `twap` execution of a plan: equal slices sent on a clock, a time-weighted average price order.

The quantity is cut into `slices`, from 2 to 60, and one is sent every `over_minutes` times 60 divided by `slices` seconds, the first at once. Units that do not divide evenly go to the earliest slices, each slice is worked out from the order's total when it falls due, so a total a join changes is spread over the slices still to come, and a slice that has not filled is left resting when the next goes. Slices are whole lots, and a slice that comes to nothing is skipped rather than stalling the order. The order starts working as soon as its trigger holds.

A TWAP can be the outer execution of a nested pair, releasing slices that an inner `IcebergExecution`, `VwapExecution`, `FrontLoadedExecution` or another TWAP works, or the inner one, working each slice of an outer execution. It cannot carry a resting stop, because a stop protects the whole position at once.

Typical usage example:

  execution = twap_execution.TwapExecution(slices=6, over_minutes=60)
  part = order_part.OrderPart(execution=execution)
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class TwapExecution(plan_part.PlanPart):
    """An execution that sends equal slices at even intervals.

    Attributes:
        slices: The int number of slices, from 2 to 60.
        over_minutes: The float number of minutes the slices are spread across, above zero.
    """

    def __init__(
        self,
        *,
        slices: int,
        over_minutes: float,
    ):
        """Initialises the execution with its slices and its span.

        Args:
            slices: The int number of slices, from 2 to 60.
            over_minutes: The float number of minutes the slices are spread across, above zero.

        Raises:
            Nothing.
        """
        self.slices = slices
        self.over_minutes = over_minutes

    def document(self) -> dict:
        """Builds the `twap` execution object UBI reads.

        Returns:
            A dict with the single key `twap`, whose value holds `slices` and `over_minutes`.

        Raises:
            Nothing.

        Examples:
            Print six slices spread across an hour, one every ten minutes:

            ```python
            from tradingmachine.orders.plan_parts import twap_execution

            execution = twap_execution.TwapExecution(slices=6, over_minutes=60)
            print(execution.document())
            ```

            Print a buy worked as twelve slices over two hours, each priced two ticks past the offer when it is sent:

            ```python
            from tradingmachine.orders.plan_parts import marketable_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import twap_execution

            part = order_part.OrderPart(
                pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
                execution=twap_execution.TwapExecution(
                    slices=12,
                    over_minutes=120,
                ),
            )
            print(part.document())
            ```

            Print an order sent as four TWAP slices over forty minutes, each shown as an iceberg of 25:

            ```python
            from tradingmachine.orders.plan_parts import iceberg_execution
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import twap_execution

            part = order_part.OrderPart(
                execution=twap_execution.TwapExecution(
                    slices=4,
                    over_minutes=40,
                ),
                inner_execution=iceberg_execution.IcebergExecution(
                    visible_quantity=25,
                ),
            )
            print(part.document())
            ```
        """
        return {
            "twap": {
                "slices": self.slices,
                "over_minutes": self.over_minutes,
            },
        }
