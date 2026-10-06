"""The `repeat` join of a plan: one order sent again and again, on a timer or once each trading day.

The child must be a plain `OrderPart`, not another join, and UBI sends it `times` times, from 1 to 100. Exactly one of `every_minutes` and `every_trading_day_at` must be given. With `every_minutes`, the first copy goes at once and each later copy that many minutes after the one before, counted from when the plan was placed. With `every_trading_day_at`, each copy goes at that time on its own trading day and the plan is kept across days. With `until`, a condition, every copy still waiting is ended once the condition holds; the order then takes no lifetime of its own. UBI also refuses, with the rule `repeat_needs_order`, a child whose presets make it a join, such as a `bracket`, and a child naming a type kept whole, such as a `grid`, because either would place its orders at once rather than wait its turn. A repeat join cannot be a `then` join's child.

Typical usage example:

  part = repeat_part.RepeatPart(
      child=order_part.OrderPart(quantity=10),
      times=6,
      every_minutes=30,
  )
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class RepeatPart(plan_part.PlanPart):
    """One order sent a number of times, spaced by minutes or by trading days.

    Attributes:
        child: The plan_part.PlanPart `OrderPart` sent each time.
        times: The int number of copies sent, from 1 to 100.
        every_minutes: The float minutes between one copy and the next, or None when `every_trading_day_at` is given.
        every_trading_day_at: The str time of day each copy is sent on its own trading day, such as `09:20`, or None when `every_minutes` is given.
        until: The plan_part.PlanPart condition that ends every copy still waiting, or None.
    """

    def __init__(
        self,
        *,
        child: plan_part.PlanPart,
        times: int,
        every_minutes: float | None = None,
        every_trading_day_at: str | None = None,
        until: plan_part.PlanPart | None = None,
    ):
        """Initialises the join with its order and schedule.

        Args:
            child: The plan_part.PlanPart sent each time, which must be a plain `OrderPart`; UBI refuses a join here, and a preset that stands for a join or a type kept whole, with the rule `repeat_needs_order`.
            times: The int number of copies, from 1 to 100.
            every_minutes: The float minutes above zero between copies, or None when `every_trading_day_at` is given.
            every_trading_day_at: The str time of day in India, such as `09:20`, at which each copy is sent on its own trading day, or None when `every_minutes` is given.
            until: A plan_part.PlanPart condition, such as `PriceCrosses` or `TimeAt`, that ends every copy still waiting once it holds, or None to let every copy run.

        Raises:
            Nothing.
        """
        self.child = child
        self.times = times
        self.every_minutes = every_minutes
        self.every_trading_day_at = every_trading_day_at
        self.until = until

    def document(self) -> dict:
        """Builds the `repeat` node UBI reads.

        Returns:
            A dict with the single key `repeat`, whose value holds `child`, `times`, and each of `every_minutes`, `every_trading_day_at` and `until` that is not None.

        Raises:
            Nothing.

        Examples:
            Print a buy of 10 sent six times, half an hour apart:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import repeat_part

            part = repeat_part.RepeatPart(
                child=order_part.OrderPart(quantity=10),
                times=6,
                every_minutes=30,
            )
            print(part.document())
            ```

            Print a buy sent at twenty past nine on each of the next five trading days, stopped once the price rises past 1050:

            ```python
            from tradingmachine.orders.plan_parts import marketable_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import price_crosses
            from tradingmachine.orders.plan_parts import repeat_part

            part = repeat_part.RepeatPart(
                child=order_part.OrderPart(
                    pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
                ),
                times=5,
                every_trading_day_at="09:20",
                until=price_crosses.PriceCrosses(
                    level=1050.0,
                    direction="at_or_above",
                ),
            )
            print(part.document())
            ```
        """
        settings = {
            "child": self.child.document(),
            "times": self.times,
        }
        if self.every_minutes is not None:
            settings["every_minutes"] = self.every_minutes
        if self.every_trading_day_at is not None:
            settings["every_trading_day_at"] = self.every_trading_day_at
        if self.until is not None:
            settings["until"] = self.until.document()
        return {
            "repeat": settings,
        }
