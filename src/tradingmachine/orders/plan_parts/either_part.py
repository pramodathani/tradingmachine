"""The `either` join of a plan: two or more plans run at once, where a fill on one acts on the others.

With the sibling rule `cancel`, the first child to fill cancels the others, which is one-cancels-other between whole plans. With `reduce`, the children share one quantity and each is kept at that quantity less what its siblings have filled, which is how a stop and a target protect one position; each child must then be a single `OrderPart`.

Typical usage example:

  part = either_part.EitherPart(
      children=[
          stop_part,
          target_part,
      ],
      sibling_rule="reduce",
  )
  document = part.document()
"""

from collections.abc import Sequence

from tradingmachine.orders.plan_parts import plan_part


class EitherPart(plan_part.PlanPart):
    """Several plans run at once, joined by what a fill on one does to the others.

    Attributes:
        children: The list of plan_part.PlanPart nodes run at once.
        sibling_rule: The str rule, `cancel` or `reduce`, for what a fill on one child does to the others.
        cancel_before_send: A bool that is True to have a child whose trigger holds cancel its siblings' resting orders before it is sent.
    """

    def __init__(
        self,
        *,
        children: Sequence[plan_part.PlanPart],
        sibling_rule: str,
        cancel_before_send: bool = False,
    ):
        """Initialises the join with its children and its sibling rule.

        Args:
            children: A sequence of two or more plan_part.PlanPart nodes to run at once.
            sibling_rule: The str rule, `cancel` for the first fill to cancel the others, or `reduce` for the children to share one quantity.
            cancel_before_send: A bool that is True to have a child whose trigger holds cancel its siblings' resting orders before it is sent.

        Raises:
            Nothing.
        """
        self.children = list(children)
        self.sibling_rule = sibling_rule
        self.cancel_before_send = cancel_before_send

    def document(self) -> dict:
        """Builds the `either` node UBI reads.

        Returns:
            A dict with the single key `either`, whose value holds `children`, `sibling_rule`, and `cancel_before_send` when it is True.

        Raises:
            Nothing.

        Examples:
            Print a stop and a target protecting one position, each shrinking as the other fills:

            ```python
            from tradingmachine.orders.plan_parts import either_part
            from tradingmachine.orders.plan_parts import fixed_pricing
            from tradingmachine.orders.plan_parts import native_stop_pricing
            from tradingmachine.orders.plan_parts import order_part

            part = either_part.EitherPart(
                children=[
                    order_part.OrderPart(
                        side="protect",
                        pricing=native_stop_pricing.NativeStopPricing(
                            trigger_price=990.0,
                            limit_price=988.0,
                        ),
                    ),
                    order_part.OrderPart(
                        side="protect",
                        pricing=fixed_pricing.FixedPricing(price=1010.0, order_type="LIMIT"),
                    ),
                ],
                sibling_rule="reduce",
            )
            print(part.document())
            ```

            Print two entries waiting on either side of a range, where the first to fill cancels the other:

            ```python
            from tradingmachine.orders.plan_parts import either_part
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import price_crosses

            part = either_part.EitherPart(
                children=[
                    order_part.OrderPart(
                        side="buy",
                        trigger=price_crosses.PriceCrosses(level=1010.0, direction="at_or_above"),
                    ),
                    order_part.OrderPart(
                        side="sell",
                        trigger=price_crosses.PriceCrosses(level=990.0, direction="at_or_below"),
                    ),
                ],
                sibling_rule="cancel",
                cancel_before_send=True,
            )
            print(part.document())
            ```
        """
        child_documents = []
        for child in self.children:
            child_documents.append(child.document())
        settings = {
            "children": child_documents,
            "sibling_rule": self.sibling_rule,
        }
        if self.cancel_before_send:
            settings["cancel_before_send"] = True
        return {
            "either": settings,
        }
