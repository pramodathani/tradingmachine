"""The `post_only` guard of a plan: a limit checked against the book before it is sent or moved, so that it rests rather than trades.

A buy is passive below the best offer and a sell above the best bid. A limit that would cross is refused with `on_crossing` `refuse`, which ends the order, or moved back to its own side's touch with `rest`; a move of a resting order that would cross is skipped with `refuse` and held at the own touch with `rest`. Indian exchanges have no post-only flag, so the book can still move while the order is in flight. It goes in `OrderPart(guard=...)`. UBI refuses it on a stop with `post_only_needs_limit`, and with pricing that means to trade at once, `MarketablePricing`, `ChasePricing`, a `PegPricing` to the `opposite_touch` or a market order, with `post_only_crosses`.

Typical usage example:

  guard = post_only_guard.PostOnlyGuard(on_crossing="rest")
  document = guard.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class PostOnlyGuard(plan_part.PlanPart):
    """A guard that keeps an order's limit from crossing the book.

    Attributes:
        on_crossing: The str action for a limit that would cross, `refuse` or `rest`, or None for UBI's default of `refuse`.
    """

    def __init__(self, *, on_crossing: str | None = None):
        """Initialises the guard with what it does to a crossing limit.

        Args:
            on_crossing: The str action for a limit that would cross, `refuse` to end the order or `rest` to move it back to its own side's touch, or None for UBI's default of `refuse`.

        Raises:
            Nothing.
        """
        self.on_crossing = on_crossing

    def document(self) -> dict:
        """Builds the `post_only` guard object UBI reads in an order's guard list.

        Returns:
            A dict with the single key `post_only`, whose value holds `on_crossing` when it is set.

        Raises:
            Nothing.

        Examples:
            Print a guard that refuses a limit that would cross:

            ```python
            from tradingmachine.orders.plan_parts import post_only_guard

            guard = post_only_guard.PostOnlyGuard()
            print(guard.document())
            ```

            Print an order pegged one tick behind the bid that is moved back to its own side rather than allowed to cross:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import peg_pricing
            from tradingmachine.orders.plan_parts import post_only_guard

            part = order_part.OrderPart(
                pricing=peg_pricing.PegPricing(offset_ticks=1),
                guard=post_only_guard.PostOnlyGuard(on_crossing="rest"),
            )
            print(part.document())
            ```
        """
        settings = {}
        if self.on_crossing is not None:
            settings["on_crossing"] = self.on_crossing
        return {
            "post_only": settings,
        }
