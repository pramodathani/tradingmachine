"""The `parent_fill` quantity of a plan: what a `then` join's first plan has filled, scaled by a ratio.

It is only for an order that is a `then` join's child, which UBI checks as `parent_fill_needs_then`. The child is resized at every fill of the first plan to `ratio` times what has filled, and with `whole_lots` the result is rounded to whole lots of the child's own instrument, so a size under one lot waits for more fills and is cancelled once the first plan has finished. An order sized this way that names an instrument the first plan trades is refused with HTTP 400, because it would only trade back what was filled. This is how a hedge on another instrument follows an entry.

Typical usage example:

  part = then_part.ThenPart(
      first=order_part.OrderPart(),
      each_fill=order_part.OrderPart(
          instrument=hedge,
          transaction_type="sell",
          quantity=parent_fill_quantity.ParentFillQuantity(ratio=0.5, whole_lots=True),
      ),
  )
  document = part.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class ParentFillQuantity(plan_part.PlanPart):
    """A quantity that is a ratio of what the first plan of a `then` join has filled.

    Attributes:
        ratio: The float ratio above zero applied to what filled, or None for UBI's default of 1.
        whole_lots: A bool that is True to round the result to whole lots of the order's own instrument.
    """

    def __init__(
        self,
        *,
        ratio: float | None = None,
        whole_lots: bool = False,
    ):
        """Initialises the quantity with its ratio.

        Args:
            ratio: The float ratio above zero, such as 0.5 for half of what filled, or None for UBI's default of 1.
            whole_lots: A bool that is True to round to whole lots of the order's own instrument, waiting for more fills while the size is under one lot and cancelling the order once the first plan has finished.

        Raises:
            Nothing.
        """
        self.ratio = ratio
        self.whole_lots = whole_lots

    def document(self) -> dict:
        """Builds the `parent_fill` quantity UBI reads.

        Returns:
            A dict with the single key `parent_fill`, whose value holds `ratio` when it is not None and `whole_lots` when it is True.

        Raises:
            Nothing.

        Examples:
            Print a buy followed by a sell of half of every fill, rounded to whole lots:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import parent_fill_quantity
            from tradingmachine.orders.plan_parts import then_part

            part = then_part.ThenPart(
                first=order_part.OrderPart(),
                each_fill=order_part.OrderPart(
                    transaction_type="sell",
                    quantity=parent_fill_quantity.ParentFillQuantity(
                        ratio=0.5,
                        whole_lots=True,
                    ),
                ),
            )
            print(part.document())
            ```

            Print the quantity alone with UBI's default ratio of one, which is the whole of what filled:

            ```python
            from tradingmachine.orders.plan_parts import parent_fill_quantity

            print(parent_fill_quantity.ParentFillQuantity().document())
            ```
        """
        settings = {}
        if self.ratio is not None:
            settings["ratio"] = self.ratio
        if self.whole_lots:
            settings["whole_lots"] = True
        return {
            "parent_fill": settings,
        }
