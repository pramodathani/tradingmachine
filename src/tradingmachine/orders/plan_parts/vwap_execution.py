"""The `vwap` execution of a plan: slices sized by how busy the market usually is, a volume-weighted average price order.

It sends `slices`, from 2 to 60, on the same clock as `TwapExecution`, but each slice takes the weight of the half hour it falls in, so slices near the busy open and close are bigger. The half hours are counted from the segment's own open, 09:15 for equity and 09:00 for currency and MCX, on the day the order starts working, and a slice after the last half hour takes the last weight. `volume_profile` gives the weights, one per half hour from the open; without it, an equity order takes UBI's NSE equity shape and a currency or commodity order gets even slices.

The span is given in one of two ways: `over_minutes`, or `until`, a time of day such as `"15:00"`, which spreads the slices from when the order starts until that time and is refused if the order starts after it. Giving both is refused. A VWAP can be the outer or the inner execution of a nested pair, and cannot carry a resting stop.

Typical usage example:

  execution = vwap_execution.VwapExecution(slices=10, until="15:00")
  part = order_part.OrderPart(execution=execution)
  document = part.document()
"""

from collections.abc import Sequence

from tradingmachine.orders.plan_parts import plan_part


class VwapExecution(plan_part.PlanPart):
    """An execution that sends slices on a clock, each sized by the volume profile of the half hour it falls in.

    Attributes:
        slices: The int number of slices, from 2 to 60.
        over_minutes: The float number of minutes the slices are spread across, or None when `until` is given.
        until: The str time of day, such as `15:00`, the slices end by, or None when `over_minutes` is given.
        volume_profile: The list of float relative weights, one per half hour from the segment's open, or None for UBI's default.
    """

    def __init__(
        self,
        *,
        slices: int,
        over_minutes: float | None = None,
        until: str | None = None,
        volume_profile: Sequence[float] | None = None,
    ):
        """Initialises the execution with its slices, its span and its profile.

        Args:
            slices: The int number of slices, from 2 to 60.
            over_minutes: The float number of minutes the slices are spread across, or None when `until` is given.
            until: The str time of day in India, `HH:MM`, the slices end by, or None when `over_minutes` is given.
            volume_profile: A sequence of float relative weights at or above zero, one per half hour from the segment's open, or None for UBI's NSE equity shape on equity and even slices elsewhere.

        Raises:
            Nothing.
        """
        self.slices = slices
        self.over_minutes = over_minutes
        self.until = until
        self.volume_profile = None
        if volume_profile is not None:
            self.volume_profile = list(volume_profile)

    def document(self) -> dict:
        """Builds the `vwap` execution object UBI reads.

        Returns:
            A dict with the single key `vwap`, whose value holds `slices`, whichever of `over_minutes` and `until` is set, and `volume_profile` when it is set.

        Raises:
            Nothing.

        Examples:
            Print ten slices spread across ninety minutes, sized by UBI's default profile:

            ```python
            from tradingmachine.orders.plan_parts import vwap_execution

            execution = vwap_execution.VwapExecution(slices=10, over_minutes=90)
            print(execution.document())
            ```

            Print slices that run from whenever the order starts until three in the afternoon:

            ```python
            from tradingmachine.orders.plan_parts import vwap_execution

            execution = vwap_execution.VwapExecution(slices=12, until="15:00")
            print(execution.document())
            ```

            Print a VWAP over the first two hours with a profile of its own, each slice shown as an iceberg:

            ```python
            from tradingmachine.orders.plan_parts import iceberg_execution
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import vwap_execution

            part = order_part.OrderPart(
                execution=vwap_execution.VwapExecution(
                    slices=8,
                    over_minutes=120,
                    volume_profile=[
                        3.0,
                        2.0,
                        1.5,
                        1.0,
                    ],
                ),
                inner_execution=iceberg_execution.IcebergExecution(
                    visible_quantity=20,
                ),
            )
            print(part.document())
            ```
        """
        settings = {}
        settings["slices"] = self.slices
        if self.over_minutes is not None:
            settings["over_minutes"] = self.over_minutes
        if self.until is not None:
            settings["until"] = self.until
        if self.volume_profile is not None:
            settings["volume_profile"] = self.volume_profile
        return {
            "vwap": settings,
        }
