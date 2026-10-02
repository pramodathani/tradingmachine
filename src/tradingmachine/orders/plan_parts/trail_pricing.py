"""The `trail` pricing rule of a plan: a stop-limit at the broker that follows the market and never moves back.

The stop is placed `points` behind the last price, or `percent` of it, and is moved after the best price seen: a sell stop follows the highest price up and a buy stop the lowest price down. It moves only when it can move by at least `step_ticks`, and every move passes UBI's repricing throttle and rate budget. Give exactly one of `points` and `percent`.

With `average_true_range`, the distance is a multiple of the average true range of bars UBI builds from its own ticks since the order started, and `points` is used until enough bars have closed, so this form takes `points` rather than `percent`.

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
        average_true_range: A bool that is True to trail by a multiple of the average true range rather than a fixed distance.
        bar_minutes: The float length in minutes of the bars the average true range is measured over, or None for UBI's default of 5.
        periods: The int number of bars averaged, at least 2, or None for UBI's default of 14.
        average_true_range_multiple: The float multiple of the average true range to trail by, or None for UBI's default of 2.
    """

    def __init__(
        self,
        *,
        limit_offset: float,
        points: float | None = None,
        percent: float | None = None,
        step_ticks: int | None = None,
        average_true_range: bool = False,
        bar_minutes: float | None = None,
        periods: int | None = None,
        average_true_range_multiple: float | None = None,
    ):
        """Initialises the rule with its distance and limit offset.

        Args:
            limit_offset: The float distance in rupees between the stop's trigger and its limit.
            points: The float trailing distance in rupees, or None when `percent` is given.
            percent: The float trailing distance as a percentage of the price, or None when `points` is given.
            step_ticks: The int smallest move in ticks, or None for UBI's default of 1.
            average_true_range: A bool that is True to trail by a multiple of the average true range, with `points` as the distance until enough bars have closed.
            bar_minutes: The float length in minutes of each bar, used with `average_true_range`, or None for UBI's default of 5.
            periods: The int number of bars averaged, at least 2, used with `average_true_range`, or None for UBI's default of 14.
            average_true_range_multiple: The float multiple of the average true range to trail by, used with `average_true_range`, or None for UBI's default of 2.

        Raises:
            Nothing.
        """
        self.limit_offset = limit_offset
        self.points = points
        self.percent = percent
        self.step_ticks = step_ticks
        self.average_true_range = average_true_range
        self.bar_minutes = bar_minutes
        self.periods = periods
        self.average_true_range_multiple = average_true_range_multiple

    def document(self) -> dict:
        """Builds the `trail` pricing object UBI reads.

        Returns:
            A dict with the single key `trail`, whose value holds `limit_offset`, whichever of `points` and `percent` is set, `step_ticks` when it is set, and an `atr` object with `bar_minutes`, `periods` and `multiple` when `average_true_range` is True.

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

            Print a stop that trails three times the average true range of ten-minute bars, five rupees behind until enough bars have closed:

            ```python
            from tradingmachine.orders.plan_parts import trail_pricing

            pricing = trail_pricing.TrailPricing(
                points=5.0,
                limit_offset=1.0,
                average_true_range=True,
                bar_minutes=10,
                average_true_range_multiple=3,
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
        if self.average_true_range:
            average_true_range_settings = {}
            if self.bar_minutes is not None:
                average_true_range_settings["bar_minutes"] = self.bar_minutes
            if self.periods is not None:
                average_true_range_settings["periods"] = self.periods
            if self.average_true_range_multiple is not None:
                average_true_range_settings["multiple"] = (
                    self.average_true_range_multiple
                )
            settings["atr"] = average_true_range_settings
        return {
            "trail": settings,
        }
