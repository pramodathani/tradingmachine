"""The `participation` execution of a plan: a fixed share of the volume the market itself trades.

On each tick it sends `percent` of the volume traded since its last slice, counting from the live quote's cumulative `volume` when the order starts working, which is as soon as its trigger holds, until the order is sent or `most_slices` have gone; UBI's default for `most_slices` is 60. Since UBI's fix of 2026-10-02 each slice is rounded down to whole lots of the instrument at the chosen broker, and a share under one lot waits for more volume, so an option order no longer stalls with nothing sent. The unfilled part of a cancelled slice is sent again by later slices, and a rejected slice stops the order.

Participation can be the outer execution of a nested pair, releasing its slices for an inner `IcebergExecution`, `TwapExecution`, `VwapExecution` or `FrontLoadedExecution` to work, but not the inner one. It cannot carry a resting stop.

Typical usage example:

  execution = participation_execution.ParticipationExecution(percent=10.0)
  part = order_part.OrderPart(execution=execution)
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class ParticipationExecution(plan_part.PlanPart):
    """An execution that sends a share of the market's traded volume on each tick.

    Attributes:
        percent: The float share of traded volume to send, above zero and at most 100.
        most_slices: The int most slices it will send, at least 1, or None for UBI's default of 60.
    """

    def __init__(
        self,
        *,
        percent: float,
        most_slices: int | None = None,
    ):
        """Initialises the execution with its share of the volume.

        Args:
            percent: The float share of traded volume to send, above zero and at most 100.
            most_slices: The int most slices it will send, at least 1, or None for UBI's default of 60.

        Raises:
            Nothing.
        """
        self.percent = percent
        self.most_slices = most_slices

    def document(self) -> dict:
        """Builds the `participation` execution object UBI reads.

        Returns:
            A dict with the single key `participation`, whose value holds `percent` and, when it is set, `most_slices`.

        Raises:
            Nothing.

        Examples:
            Print an order that takes a tenth of the volume as it trades:

            ```python
            from tradingmachine.orders.plan_parts import participation_execution

            execution = participation_execution.ParticipationExecution(
                percent=10.0,
            )
            print(execution.document())
            ```

            Print a five percent participation that sends at most twenty slices:

            ```python
            from tradingmachine.orders.plan_parts import participation_execution

            execution = participation_execution.ParticipationExecution(
                percent=5.0,
                most_slices=20,
            )
            print(execution.document())
            ```

            Print a participation whose every slice is shown as an iceberg of ten:

            ```python
            from tradingmachine.orders.plan_parts import iceberg_execution
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import participation_execution

            part = order_part.OrderPart(
                execution=participation_execution.ParticipationExecution(
                    percent=15.0,
                ),
                inner_execution=iceberg_execution.IcebergExecution(
                    visible_quantity=10,
                ),
            )
            print(part.document())
            ```
        """
        settings = {}
        settings["percent"] = self.percent
        if self.most_slices is not None:
            settings["most_slices"] = self.most_slices
        return {
            "participation": settings,
        }
