"""The `chase` pricing rule of a plan: a limit that starts on its own side of the book and walks towards the other until it fills.

The order starts at its own touch, and every `step_seconds` it moves `step_ticks` towards the market from where it actually is, never past the other side's touch. With `cross_after_seconds`, once that long has passed the order is moved to the other side's touch, where it fills against what is resting. A cap beside the rule holds every step.

Typical usage example:

  pricing = chase_pricing.ChasePricing(step_ticks=1, step_seconds=5)
  document = pricing.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class ChasePricing(plan_part.PlanPart):
    """A pricing rule that steps a limit from its own side of the book towards the other side.

    Attributes:
        step_ticks: The int number of ticks each step moves, at least 1, or None for UBI's default of 1.
        step_seconds: The float number of seconds between steps, above zero, or None for UBI's default of 5.
        cross_after_seconds: The float number of seconds after which the order is moved to the other side's touch, or None to walk until it reaches the touch.
    """

    def __init__(
        self,
        *,
        step_ticks: int | None = None,
        step_seconds: float | None = None,
        cross_after_seconds: float | None = None,
    ):
        """Initialises the rule with its step and timing.

        Args:
            step_ticks: The int number of ticks each step moves, at least 1, or None for UBI's default of 1.
            step_seconds: The float number of seconds between steps, above zero, or None for UBI's default of 5.
            cross_after_seconds: The float number of seconds after which the order is moved to the other side's touch, above zero, or None to keep walking.

        Raises:
            Nothing.
        """
        self.step_ticks = step_ticks
        self.step_seconds = step_seconds
        self.cross_after_seconds = cross_after_seconds

    def document(self) -> dict:
        """Builds the `chase` pricing object UBI reads, holding every setting that is not None.

        Returns:
            A dict with the single key `chase`, whose value holds `step_ticks`, `step_seconds` and `cross_after_seconds` when each is set.

        Raises:
            Nothing.

        Examples:
            Print a chase that uses UBI's defaults of one tick every five seconds:

            ```python
            from tradingmachine.orders.plan_parts import chase_pricing

            pricing = chase_pricing.ChasePricing()
            print(pricing.document())
            ```

            Print a chase that steps two ticks every ten seconds and crosses the book after a minute:

            ```python
            from tradingmachine.orders.plan_parts import chase_pricing

            pricing = chase_pricing.ChasePricing(
                step_ticks=2,
                step_seconds=10,
                cross_after_seconds=60,
            )
            print(pricing.document())
            ```
        """
        settings = {}
        if self.step_ticks is not None:
            settings["step_ticks"] = self.step_ticks
        if self.step_seconds is not None:
            settings["step_seconds"] = self.step_seconds
        if self.cross_after_seconds is not None:
            settings["cross_after_seconds"] = self.cross_after_seconds
        return {
            "chase": settings,
        }
