"""The `candle_closes` trigger of a plan: a whole bar closing past a level, rather than any tick touching it.

UBI builds the bars itself from the last traded price it sees, aligned to the clock and `bar_minutes` long, 5 minutes by default. The condition answers once per bar, at its close, so a wick through the level does not count, and nothing is known until the first bar after the order rests has closed. With no direction, a position opened with a buy waits for a close at or below the level and one opened with a sell for a close at or above it, which is a stop's meaning.

Typical usage example:

  condition = candle_closes.CandleCloses(level=995.0, bar_minutes=15)
  document = condition.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class CandleCloses(plan_part.PlanPart):
    """A condition that holds when a bar UBI builds from its own ticks closes past a level.

    Attributes:
        level: The float level in rupees that a close must reach.
        direction: The str direction, `at_or_above` or `at_or_below`, or None to take it from the side that opened the position.
        bar_minutes: The float length of one bar in minutes, or None for UBI's default of 5.
    """

    def __init__(
        self,
        *,
        level: float,
        direction: str | None = None,
        bar_minutes: float | None = None,
    ):
        """Initialises the condition with its level and settings.

        Args:
            level: The float level in rupees, above zero.
            direction: The str direction, `at_or_above` or `at_or_below`, or None for a long to wait for a close at or below the level and a short for one at or above it.
            bar_minutes: The float length of one bar in minutes, above zero, or None for UBI's default of 5.

        Raises:
            Nothing.
        """
        self.level = level
        self.direction = direction
        self.bar_minutes = bar_minutes

    def document(self) -> dict:
        """Builds the `candle_closes` condition UBI reads, holding every setting that is not None.

        Returns:
            A dict with the single key `candle_closes`, whose value holds `level` and each other setting that is set.

        Raises:
            Nothing.

        Examples:
            Print a condition on a five-minute close, with the direction taken from the opening side:

            ```python
            from tradingmachine.orders.plan_parts import candle_closes

            condition = candle_closes.CandleCloses(level=995.0)
            print(condition.document())
            ```

            Print a condition on a fifteen-minute close at or above 1010:

            ```python
            from tradingmachine.orders.plan_parts import candle_closes

            condition = candle_closes.CandleCloses(
                level=1010.0,
                direction="at_or_above",
                bar_minutes=15,
            )
            print(condition.document())
            ```

            Print a protecting order that leaves at market only once a five-minute bar closes below 990:

            ```python
            from tradingmachine.orders.plan_parts import candle_closes
            from tradingmachine.orders.plan_parts import marketable_pricing
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                side="protect",
                trigger=candle_closes.CandleCloses(level=990.0),
                pricing=marketable_pricing.MarketablePricing(),
            )
            print(part.document())
            ```
        """
        settings = {
            "level": self.level,
        }
        if self.direction is not None:
            settings["direction"] = self.direction
        if self.bar_minutes is not None:
            settings["bar_minutes"] = self.bar_minutes
        return {
            "candle_closes": settings,
        }
