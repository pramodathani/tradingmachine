"""The `trails` trigger of a plan: the last price pulling back from its best by a distance.

For an order sent as a sell, the best is the highest price seen and the pullback a fall; for a buy, the lowest price seen and a rise. It is a trailing stop kept inside UBI's order engine, so the order it fires can be priced any way, but it does nothing while the engine is down. Give exactly one of `points` and `percent`.

Typical usage example:

  condition = trails.Trails(points=5.0)
  document = condition.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class Trails(plan_part.PlanPart):
    """A condition that holds once the last price has pulled back from its best by a distance.

    Attributes:
        points: The float distance in rupees, or None when `percent` is given.
        percent: The float distance as a percentage of the price, or None when `points` is given.
    """

    def __init__(
        self,
        *,
        points: float | None = None,
        percent: float | None = None,
    ):
        """Initialises the condition with its distance.

        Args:
            points: The float distance in rupees, or None when `percent` is given.
            percent: The float distance as a percentage of the price, or None when `points` is given.

        Raises:
            Nothing.
        """
        self.points = points
        self.percent = percent

    def document(self) -> dict:
        """Builds the `trails` condition UBI reads.

        Returns:
            A dict with the single key `trails`, whose value holds whichever of `points` and `percent` is set.

        Raises:
            Nothing.

        Examples:
            Print a condition that holds after a pullback of five rupees:

            ```python
            from tradingmachine.orders.plan_parts import trails

            print(trails.Trails(points=5.0).document())
            ```

            Print a condition that holds after a pullback of one and a half percent:

            ```python
            from tradingmachine.orders.plan_parts import trails

            print(trails.Trails(percent=1.5).document())
            ```
        """
        settings = {}
        if self.points is not None:
            settings["points"] = self.points
        if self.percent is not None:
            settings["percent"] = self.percent
        return {
            "trails": settings,
        }
