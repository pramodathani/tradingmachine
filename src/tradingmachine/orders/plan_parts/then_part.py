"""The `then` join of a plan: a first plan, and a child plan started once the first one fills.

With `each_fill`, the child starts on the first plan's first fill, sized to what has filled, and is resized as more fills arrive, which is how a stop or a target follows an entry. A `protect` or `close` order in the child works against the side the first plan actually filled on, and when both sides of a two-sided entry filled and the later side filled more, UBI cancels the exits resting on the old side and sends them again on the new side, priced from the fills on the side now held. An exit that has finished is sent again only once its target grows past what it had when it finished, so an exit the exchange cancels is not simply sent again. With `on_complete`, the child waits until the first plan is done. Give exactly one of the two.

Typical usage example:

  part = then_part.ThenPart(
      first=order_part.OrderPart(),
      each_fill=order_part.OrderPart(
          side="protect",
          pricing=trail_pricing.TrailPricing(points=5.0, limit_offset=1.0),
      ),
  )
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class ThenPart(plan_part.PlanPart):
    """A first plan and the child plan it starts when it fills.

    Attributes:
        first: The plan_part.PlanPart node that runs first.
        each_fill: The plan_part.PlanPart node started on the first fill and resized with every fill, or None.
        on_complete: The plan_part.PlanPart node started once the first plan is done, or None.
        cancel_first_on_child_fill: A bool that is True to cancel whatever of the first plan is still working once the child fills anything.
    """

    def __init__(
        self,
        *,
        first: plan_part.PlanPart,
        each_fill: plan_part.PlanPart | None = None,
        on_complete: plan_part.PlanPart | None = None,
        cancel_first_on_child_fill: bool = False,
    ):
        """Initialises the join with its two plans.

        Args:
            first: The plan_part.PlanPart node that runs first, an `OrderPart` or another join.
            each_fill: The plan_part.PlanPart node to start on the first fill and resize with every fill, or None when `on_complete` is given.
            on_complete: The plan_part.PlanPart node to start once the first plan is done, or None when `each_fill` is given.
            cancel_first_on_child_fill: A bool that is True to cancel whatever of the first plan is still working once the child fills anything.

        Raises:
            Nothing.
        """
        self.first = first
        self.each_fill = each_fill
        self.on_complete = on_complete
        self.cancel_first_on_child_fill = cancel_first_on_child_fill

    def document(self) -> dict:
        """Builds the `then` node UBI reads.

        Returns:
            A dict with the single key `then`, whose value holds `first`, whichever of `each_fill` and `on_complete` is set, and `cancel_first_on_child_fill` when it is True.

        Raises:
            Nothing.

        Examples:
            Print an entry followed by a trailing stop sized to each of its fills:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import then_part
            from tradingmachine.orders.plan_parts import trail_pricing

            part = then_part.ThenPart(
                first=order_part.OrderPart(),
                each_fill=order_part.OrderPart(
                    side="protect",
                    pricing=trail_pricing.TrailPricing(points=5.0, limit_offset=1.0),
                ),
            )
            print(part.document())
            ```

            Print an entry whose exit waits until the entry is done, and cancels the rest of the entry once it fills:

            ```python
            from tradingmachine.orders.plan_parts import fixed_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import then_part

            part = then_part.ThenPart(
                first=order_part.OrderPart(),
                on_complete=order_part.OrderPart(
                    side="protect",
                    pricing=fixed_pricing.FixedPricing(price=1010.0, order_type="LIMIT"),
                ),
                cancel_first_on_child_fill=True,
            )
            print(part.document())
            ```
        """
        settings = {
            "first": self.first.document(),
        }
        if self.each_fill is not None:
            settings["each_fill"] = self.each_fill.document()
        if self.on_complete is not None:
            settings["on_complete"] = self.on_complete.document()
        if self.cancel_first_on_child_fill:
            settings["cancel_first_on_child_fill"] = True
        return {
            "then": settings,
        }
