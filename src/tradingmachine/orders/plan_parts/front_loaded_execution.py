"""The `front_loaded` execution of a plan: slices that shrink as they go, so most of the order trades early, an implementation shortfall order.

It sends `slices`, from 2 to 60, on the same clock as `TwapExecution`, one every `over_minutes` times 60 divided by `slices` seconds, the first at once. Each slice is `1 - urgency × 0.5` of the one before, so an urgency of 0 is an even split and an urgency of 1 halves every slice; UBI's default urgency is 0.5, each slice three quarters of the last. Slices are whole lots, and a slice that comes to nothing is skipped.

It can be the outer or the inner execution of a nested pair, and cannot carry a resting stop.

Typical usage example:

  execution = front_loaded_execution.FrontLoadedExecution(
      slices=5,
      over_minutes=30,
  )
  part = order_part.OrderPart(execution=execution)
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class FrontLoadedExecution(plan_part.PlanPart):
    """An execution that sends slices on a clock, each a fixed share smaller than the one before.

    Attributes:
        slices: The int number of slices, from 2 to 60.
        over_minutes: The float number of minutes the slices are spread across, above zero.
        urgency: The float from 0 to 1 saying how front-loaded the schedule is, or None for UBI's default of 0.5.
    """

    def __init__(
        self,
        *,
        slices: int,
        over_minutes: float,
        urgency: float | None = None,
    ):
        """Initialises the execution with its slices, its span and its urgency.

        Args:
            slices: The int number of slices, from 2 to 60.
            over_minutes: The float number of minutes the slices are spread across, above zero.
            urgency: The float from 0, an even split, to 1, each slice half the one before, or None for UBI's default of 0.5.

        Raises:
            Nothing.
        """
        self.slices = slices
        self.over_minutes = over_minutes
        self.urgency = urgency

    def document(self) -> dict:
        """Builds the `front_loaded` execution object UBI reads.

        Returns:
            A dict with the single key `front_loaded`, whose value holds `slices`, `over_minutes` and, when it is set, `urgency`.

        Raises:
            Nothing.

        Examples:
            Print five slices over half an hour at UBI's default urgency:

            ```python
            from tradingmachine.orders.plan_parts import front_loaded_execution

            execution = front_loaded_execution.FrontLoadedExecution(
                slices=5,
                over_minutes=30,
            )
            print(execution.document())
            ```

            Print the most urgent schedule, each slice half the one before:

            ```python
            from tradingmachine.orders.plan_parts import front_loaded_execution

            execution = front_loaded_execution.FrontLoadedExecution(
                slices=4,
                over_minutes=20,
                urgency=1.0,
            )
            print(execution.document())
            ```

            Print an order sent front-loaded over an hour, each slice shown as an iceberg of fifty:

            ```python
            from tradingmachine.orders.plan_parts import front_loaded_execution
            from tradingmachine.orders.plan_parts import iceberg_execution
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                execution=front_loaded_execution.FrontLoadedExecution(
                    slices=6,
                    over_minutes=60,
                    urgency=0.8,
                ),
                inner_execution=iceberg_execution.IcebergExecution(
                    visible_quantity=50,
                ),
            )
            print(part.document())
            ```
        """
        settings = {}
        settings["slices"] = self.slices
        settings["over_minutes"] = self.over_minutes
        if self.urgency is not None:
            settings["urgency"] = self.urgency
        return {
            "front_loaded": settings,
        }
