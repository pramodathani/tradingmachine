"""The `iceberg` execution of a plan: only part of the order shown at a time.

The order is sent as pieces of `visible_quantity`, the next only once the last has filled. Each piece may vary by up to `randomise_percent` either way, worked out from the parent's id and the number of pieces sent, so another trader cannot spot a repeating size; UBI's default is 0, no variation. A piece that is cancelled or rejected rather than filled stops the iceberg.

An iceberg can nest on either side. As the outer execution it releases its pieces as slices for an inner one to work, and as the inner execution it shows each slice of a `TwapExecution`, `VwapExecution`, `FrontLoadedExecution`, `ParticipationExecution` or another iceberg a little at a time.

Typical usage example:

  execution = iceberg_execution.IcebergExecution(visible_quantity=10)
  part = order_part.OrderPart(execution=execution)
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class IcebergExecution(plan_part.PlanPart):
    """An execution that shows a small piece of the order at a time and sends the next once it has filled.

    Attributes:
        visible_quantity: The int size of each piece before any variation, at least 1.
        randomise_percent: The int percentage, 0 to 99, by which a piece may vary either way, or None for UBI's default of 0.
    """

    def __init__(
        self,
        *,
        visible_quantity: int,
        randomise_percent: int | None = None,
    ):
        """Initialises the execution with its piece size.

        Args:
            visible_quantity: The int size of each piece before any variation, at least 1.
            randomise_percent: The int percentage, 0 to 99, by which a piece may vary either way, or None for UBI's default of 0.

        Raises:
            Nothing.
        """
        self.visible_quantity = visible_quantity
        self.randomise_percent = randomise_percent

    def document(self) -> dict:
        """Builds the `iceberg` execution object UBI reads.

        Returns:
            A dict with the single key `iceberg`, whose value holds `visible_quantity` and, when it is set, `randomise_percent`.

        Raises:
            Nothing.

        Examples:
            Print an iceberg that shows ten units at a time:

            ```python
            from tradingmachine.orders.plan_parts import iceberg_execution

            execution = iceberg_execution.IcebergExecution(visible_quantity=10)
            print(execution.document())
            ```

            Print an iceberg whose pieces vary by up to a fifth either way:

            ```python
            from tradingmachine.orders.plan_parts import iceberg_execution

            execution = iceberg_execution.IcebergExecution(
                visible_quantity=50,
                randomise_percent=20,
            )
            print(execution.document())
            ```

            Print an order sent as six TWAP slices over an hour, each slice shown as an iceberg of ten:

            ```python
            from tradingmachine.orders.plan_parts import iceberg_execution
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import twap_execution

            part = order_part.OrderPart(
                execution=twap_execution.TwapExecution(
                    slices=6,
                    over_minutes=60,
                ),
                inner_execution=iceberg_execution.IcebergExecution(
                    visible_quantity=10,
                ),
            )
            print(part.document())
            ```
        """
        settings = {}
        settings["visible_quantity"] = self.visible_quantity
        if self.randomise_percent is not None:
            settings["randomise_percent"] = self.randomise_percent
        return {
            "iceberg": settings,
        }
