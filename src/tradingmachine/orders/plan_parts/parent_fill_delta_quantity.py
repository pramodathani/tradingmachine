"""The `parent_fill_delta` quantity of a plan: what a `then` join's first plan filled, scaled by the delta of the option the plan trades.

It is for a delta hedge. The plan's own instrument must be an option, or UBI refuses the plan, and at each fill UBI works out the option's Black-76 delta at `volatility` percent, using the last price of the order's own instrument, usually the future, as the forward. The order must be a `then` join's child (`parent_fill_needs_then`), and an order with side `against_delta` must have this quantity (`against_delta_needs_delta`); that side sells against a bought call and buys against a bought put. With `whole_lots` the size is rounded to whole lots of the order's own instrument. An expired option, or a forward with no price, leaves the size as it was.

Typical usage example:

  part = then_part.ThenPart(
      first=order_part.OrderPart(),
      each_fill=order_part.OrderPart(
          instrument=future,
          side="against_delta",
          quantity=parent_fill_delta_quantity.ParentFillDeltaQuantity(volatility=12.5, whole_lots=True),
      ),
  )
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class ParentFillDeltaQuantity(plan_part.PlanPart):
    """A quantity that is what an option entry filled times that option's delta.

    Attributes:
        volatility: The float volatility in percent the delta is worked out at.
        whole_lots: A bool that is True to round the result to whole lots of the order's own instrument.
    """

    def __init__(
        self,
        *,
        volatility: float,
        whole_lots: bool = False,
    ):
        """Initialises the quantity with the volatility its delta is worked out at.

        Args:
            volatility: The float annual volatility in percent above zero, such as 12.5.
            whole_lots: A bool that is True to round to whole lots of the order's own instrument.

        Raises:
            Nothing.
        """
        self.volatility = volatility
        self.whole_lots = whole_lots

    def document(self) -> dict:
        """Builds the `parent_fill_delta` quantity UBI reads.

        Returns:
            A dict with the single key `parent_fill_delta`, whose value holds `volatility`, and `whole_lots` when it is True.

        Raises:
            Nothing.

        Examples:
            Print an option buy followed by a hedge against its delta at 12.5% volatility, in whole lots:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import parent_fill_delta_quantity
            from tradingmachine.orders.plan_parts import then_part

            part = then_part.ThenPart(
                first=order_part.OrderPart(),
                each_fill=order_part.OrderPart(
                    side="against_delta",
                    quantity=parent_fill_delta_quantity.ParentFillDeltaQuantity(
                        volatility=12.5,
                        whole_lots=True,
                    ),
                ),
            )
            print(part.document())
            ```

            Print the quantity alone at 18% volatility, unrounded:

            ```python
            from tradingmachine.orders.plan_parts import parent_fill_delta_quantity

            quantity = parent_fill_delta_quantity.ParentFillDeltaQuantity(volatility=18.0)
            print(quantity.document())
            ```
        """
        settings = {
            "volatility": self.volatility,
        }
        if self.whole_lots:
            settings["whole_lots"] = True
        return {
            "parent_fill_delta": settings,
        }
