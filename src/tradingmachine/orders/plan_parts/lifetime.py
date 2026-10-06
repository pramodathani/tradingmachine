"""The lifetime of an order in a plan: when it stops, which part of its life that bounds, and what is done then.

A lifetime ends exactly one way: `at_time`, a time of day on the instrument's next trading day; `after_minutes`, counted from when the plan is placed; `after_days`, 1 to 365 days of 24 hours from then, which keeps the plan alive across trading days; or `when`, any trigger condition, checked on every tick. `applies_to` says whether the end bounds the wait for the trigger, the time the order works after it is sent, or both, which is UBI's default. An order still waiting when its end comes is done as expired. An order working then ends by `on_end`: `cancel`, UBI's default, cancels what rests and keeps what filled; `marketable` moves what rests two ticks past the other side's touch so it fills, which a stop cannot do; and `close_filled` cancels what rests and closes what filled at market, which only a plan that is this one order can do, and not an order that protects a position. A part ended by `close_filled` is done with the reason `closed`, or `expired` when nothing had filled.

Unlike the other parts, a lifetime is an entry of the order's `lifetime` list rather than a value under one key, so its `document()` holds the settings directly. A `RepeatPart` with `until` gives each copy a lifetime of its own, so an order repeated that way takes no `Lifetime`.

Typical usage example:

  ending = lifetime.Lifetime(at_time="14:30", on_end="marketable")
  document = ending.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class Lifetime(plan_part.PlanPart):
    """When an order of a plan stops working, and what is done with it then.

    Attributes:
        at_time: The str time of day the order ends at, such as `14:30`, or None.
        after_minutes: The float minutes after placing that the order ends, or None.
        after_days: The int days after placing that the order ends, from 1 to 365, or None.
        when: The plan_part.PlanPart condition that ends the order when it holds, or None.
        applies_to: The str part of the order's life the end bounds, `waiting`, `working` or `both`, or None for `both`.
        on_end: The str action taken on a working order, `cancel`, `marketable` or `close_filled`, or None for `cancel`.
    """

    def __init__(
        self,
        *,
        at_time: str | None = None,
        after_minutes: float | None = None,
        after_days: int | None = None,
        when: plan_part.PlanPart | None = None,
        applies_to: str | None = None,
        on_end: str | None = None,
    ):
        """Initialises the lifetime with its end and settings.

        Exactly one of `at_time`, `after_minutes`, `after_days` and `when` must be given; UBI refuses none or more than one.

        Args:
            at_time: The str time of day in India the order ends at, such as `14:30`, on the instrument's next trading day, or None.
            after_minutes: The float minutes after the plan is placed that the order ends, above zero, or None. UBI refuses minutes on a day the instrument does not trade.
            after_days: The int days of 24 hours after the plan is placed that the order ends, from 1 to 365, or None.
            when: A plan_part.PlanPart trigger condition, such as `PriceCrosses`, `TimeAt`, `AccountCondition` or `AnyCondition`, that ends the order when it holds, or None.
            applies_to: The str part of the order's life the end bounds, `waiting` for the wait for its trigger, `working` for the time after it is sent, or `both`, or None for UBI's default of `both`.
            on_end: The str action taken on an order still working, `cancel` to cancel what rests, `marketable` to move what rests past the other side's touch, or `close_filled` to cancel what rests and close what filled at market, or None for UBI's default of `cancel`.

        Raises:
            Nothing.
        """
        self.at_time = at_time
        self.after_minutes = after_minutes
        self.after_days = after_days
        self.when = when
        self.applies_to = applies_to
        self.on_end = on_end

    def document(self) -> dict:
        """Builds the lifetime entry UBI reads, holding every setting that is not None.

        Returns:
            A dict holding each setting that is set, with `when` as its condition's object. It is one entry of the order's `lifetime` list, which `OrderPart` builds.

        Raises:
            Nothing.

        Examples:
            Print a lifetime that ends at 14:30 and moves what still rests past the touch so it fills:

            ```python
            from tradingmachine.orders.plan_parts import lifetime

            ending = lifetime.Lifetime(at_time="14:30", on_end="marketable")
            print(ending.document())
            ```

            Print an order whose wait ends when the price falls to 990 or when it is ten past three, whichever comes first:

            ```python
            from tradingmachine.orders.plan_parts import any_condition
            from tradingmachine.orders.plan_parts import lifetime
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import price_crosses
            from tradingmachine.orders.plan_parts import time_at

            part = order_part.OrderPart(
                trigger=price_crosses.PriceCrosses(level=1010.0),
                lifetime=lifetime.Lifetime(
                    when=any_condition.AnyCondition(
                        [
                            price_crosses.PriceCrosses(
                                level=990.0,
                                direction="at_or_below",
                            ),
                            time_at.TimeAt("15:10"),
                        ]
                    ),
                    applies_to="waiting",
                    on_end="cancel",
                ),
            )
            print(part.document())
            ```

            Print an intraday entry that closes whatever filled thirty minutes after it is placed:

            ```python
            from tradingmachine.orders.plan_parts import lifetime
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                lifetime=lifetime.Lifetime(
                    after_minutes=30,
                    on_end="close_filled",
                ),
            )
            print(part.document())
            ```
        """
        settings = {}
        if self.at_time is not None:
            settings["at_time"] = self.at_time
        if self.after_minutes is not None:
            settings["after_minutes"] = self.after_minutes
        if self.after_days is not None:
            settings["after_days"] = self.after_days
        if self.when is not None:
            settings["when"] = self.when.document()
        if self.applies_to is not None:
            settings["applies_to"] = self.applies_to
        if self.on_end is not None:
            settings["on_end"] = self.on_end
        return settings
