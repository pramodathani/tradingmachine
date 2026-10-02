"""The `trail` pricing rule of a plan: a stop-limit at the broker that follows the market and never moves back.

The stop is placed `points` behind the last price, or `percent` of it, and is moved after the best price seen: a sell stop follows the highest price up and a buy stop the lowest price down. It moves only when it can move by at least `step_ticks`, and every move passes UBI's repricing throttle and rate budget. Give exactly one of `points` and `percent`.

Typical usage example:

  pricing = trail_pricing.TrailPricing(points=5.0, limit_offset=1.0)
  document = pricing.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class TrailPricing(plan_part.PlanPart):
    """A pricing rule that rests a stop-limit at the broker and trails it behind the market.

    Attributes:
        points: The float trailing distance in rupees, or None when `percent` is given.
        percent: The float trailing distance as a percentage of the price, or None when `points` is given.
        limit_offset: The float distance in rupees between the stop's trigger and its limit.
        step_ticks: The int smallest move in ticks, or None for UBI's default of 1.
    """

    def __init__(
        self,
        *,
        limit_offset: float,
        points: float | None = None,
        percent: float | None = None,
        step_ticks: int | None = None,
    ):
        """Initialises the rule with its distance and limit offset.

        Args:
            limit_offset: The float distance in rupees between the stop's trigger and its limit.
            points: The float trailing distance in rupees, or None when `percent` is given.
            percent: The float trailing distance as a percentage of the price, or None when `points` is given.
            step_ticks: The int smallest move in ticks, or None for UBI's default of 1.

        Raises:
            Nothing.
        """
        self.limit_offset = limit_offset
        self.points = points
        self.percent = percent
        self.step_ticks = step_ticks

    def document(self) -> dict:
        """Builds the `trail` pricing object UBI reads.

        Returns:
            A dict with the single key `trail`, whose value holds `limit_offset`, whichever of `points` and `percent` is set, and `step_ticks` when it is set.

        Raises:
            Nothing.

        Examples:
            Print a stop that trails five rupees behind the market:

            ```python
            from tradingmachine.orders.plan_parts import trail_pricing

            pricing = trail_pricing.TrailPricing(points=5.0, limit_offset=1.0)
            print(pricing.document())
            ```

            Print a stop that trails two percent behind and moves only in steps of four ticks:

            ```python
            from tradingmachine.orders.plan_parts import trail_pricing

            pricing = trail_pricing.TrailPricing(
                percent=2.0,
                limit_offset=1.0,
                step_ticks=4,
            )
            print(pricing.document())
            ```
        """
        settings = {}
        if self.points is not None:
            settings["points"] = self.points
        if self.percent is not None:
            settings["percent"] = self.percent
        settings["limit_offset"] = self.limit_offset
        if self.step_ticks is not None:
            settings["step_ticks"] = self.step_ticks
        return {
            "trail": settings,
        }
