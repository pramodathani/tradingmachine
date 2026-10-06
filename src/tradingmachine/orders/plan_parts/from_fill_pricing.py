"""The `from_fill` pricing rule of a plan: an exit placed a distance from the price its position was opened at.

UBI prices the exit from the average fill of the orders that opened the position, in the direction that suits the side it is sent on, so one setting suits a position opened either way. When both sides of a two-sided entry filled, only the fills on the side the position is held on count, so a short opened at 990 and partly bought back at 1010 keeps its exits measured from 990. With `stop_distance` the exit is a native stop-limit that far beyond the fill against the position, with its limit `stop_limit_offset` further on; with `target_distance` it is a limit that far beyond the fill in the position's favour. Give the stop pair or the target, not both. Prices are rounded to the tick, and nothing is sent until the opening order has filled. The order must sit under a `ThenPart`'s `each_fill` or `on_complete` child, or UBI refuses the plan with `from_fill_needs_then`.

Typical usage example:

  pricing = from_fill_pricing.FromFillPricing(
      stop_distance=10.0,
      stop_limit_offset=1.0,
  )
  document = pricing.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class FromFillPricing(plan_part.PlanPart):
    """A pricing rule for an exit set a distance from the fill that opened its position.

    Attributes:
        stop_distance: The float distance in rupees from the fill to the stop's trigger, or None for a target.
        stop_limit_offset: The float distance in rupees past the stop's trigger to its limit, or None for a target.
        target_distance: The float distance in rupees from the fill to the target's limit, or None for a stop.
    """

    def __init__(
        self,
        *,
        stop_distance: float | None = None,
        stop_limit_offset: float | None = None,
        target_distance: float | None = None,
    ):
        """Initialises the rule as a stop or as a target.

        Args:
            stop_distance: The float distance in rupees from the fill to the stop's trigger, given with `stop_limit_offset`, or None for a target.
            stop_limit_offset: The float distance in rupees past the stop's trigger to its limit, given with `stop_distance`, or None for a target.
            target_distance: The float distance in rupees from the fill to the target's limit, or None for a stop.

        Raises:
            Nothing.
        """
        self.stop_distance = stop_distance
        self.stop_limit_offset = stop_limit_offset
        self.target_distance = target_distance

    def document(self) -> dict:
        """Builds the `from_fill` pricing object UBI reads, holding every setting that is not None.

        Returns:
            A dict with the single key `from_fill`, whose value holds `stop_distance`, `stop_limit_offset` and `target_distance` when each is set.

        Raises:
            Nothing.

        Examples:
            Print a stop ten rupees from the fill with its limit one rupee past the trigger:

            ```python
            from tradingmachine.orders.plan_parts import from_fill_pricing

            pricing = from_fill_pricing.FromFillPricing(
                stop_distance=10.0,
                stop_limit_offset=1.0,
            )
            print(pricing.document())
            ```

            Print an entry followed by a stop and a target measured from its fill, which share the position so a fill on one reduces the other:

            ```python
            from tradingmachine.orders.plan_parts import either_part
            from tradingmachine.orders.plan_parts import from_fill_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import then_part

            part = then_part.ThenPart(
                first=order_part.OrderPart(),
                each_fill=either_part.EitherPart(
                    children=[
                        order_part.OrderPart(
                            side="protect",
                            pricing=from_fill_pricing.FromFillPricing(
                                stop_distance=10.0,
                                stop_limit_offset=1.0,
                            ),
                        ),
                        order_part.OrderPart(
                            side="protect",
                            pricing=from_fill_pricing.FromFillPricing(
                                target_distance=20.0,
                            ),
                        ),
                    ],
                    sibling_rule="reduce",
                ),
            )
            print(part.document())
            ```
        """
        settings = {}
        if self.stop_distance is not None:
            settings["stop_distance"] = self.stop_distance
        if self.stop_limit_offset is not None:
            settings["stop_limit_offset"] = self.stop_limit_offset
        if self.target_distance is not None:
            settings["target_distance"] = self.target_distance
        return {
            "from_fill": settings,
        }
