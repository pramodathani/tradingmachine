"""The `together` join of a plan: one to twenty-five plans started at once, each trading its own quantity.

Unlike an `either` join, a fill on one child does nothing to the others, so a together join is how a plan sends a basket, a pair or a spread whose legs are independent. By default UBI's broker selector chooses a broker that can afford the whole group, and `hedge_benefit` prices hedged legs as one position. With `done_when` set to `any`, the rest are cancelled once one child is done. A together join cannot be a `then` join's child, because that child is sized to the first plan's fills.

Typical usage example:

  part = together_part.TogetherPart(
      children=[
          order_part.OrderPart(transaction_type="buy"),
          order_part.OrderPart(transaction_type="sell"),
      ],
      hedge_benefit=True,
  )
  document = part.document()
"""

from collections.abc import Sequence

from tradingmachine.orders.plan_parts import plan_part


class TogetherPart(plan_part.PlanPart):
    """Several plans started at once, each trading its own quantity.

    Attributes:
        children: The list of plan_part.PlanPart nodes started at once.
        group_margin: A bool that is False to let each child choose its broker alone, or None for UBI's default of True.
        hedge_benefit: A bool that is True to price hedged children together as one position when checking the broker can afford them.
        done_when: The str rule, `all` or `any`, for when the join is done, or None for UBI's default of `all`.
    """

    def __init__(
        self,
        *,
        children: Sequence[plan_part.PlanPart],
        group_margin: bool | None = None,
        hedge_benefit: bool = False,
        done_when: str | None = None,
    ):
        """Initialises the join with its children and settings.

        Args:
            children: A sequence of one to twenty-five plan_part.PlanPart nodes, each an `OrderPart` or another join.
            group_margin: A bool that is True for the broker selector to choose a broker that can afford the whole group, False for each child to choose alone, or None for UBI's default of True.
            hedge_benefit: A bool that is True to price options and futures on one underlying and expiry together as one hedged position when checking the broker can afford the group.
            done_when: The str rule `all` for the join to be done once every child is done, `any` to cancel the rest once one child is done, or None for UBI's default of `all`.

        Raises:
            Nothing.
        """
        self.children = list(children)
        self.group_margin = group_margin
        self.hedge_benefit = hedge_benefit
        self.done_when = done_when

    def document(self) -> dict:
        """Builds the `together` node UBI reads.

        Returns:
            A dict with the single key `together`, whose value holds `children`, `group_margin` and `done_when` when they are not None, and `hedge_benefit` when it is True.

        Raises:
            Nothing.

        Examples:
            Print a buy and a sell started at once, priced together as one hedged position:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import together_part

            part = together_part.TogetherPart(
                children=[
                    order_part.OrderPart(transaction_type="buy", quantity=10),
                    order_part.OrderPart(transaction_type="sell", quantity=10),
                ],
                hedge_benefit=True,
            )
            print(part.document())
            ```

            Print two dip entries at different levels where the first to complete cancels the other, each choosing its broker alone:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import price_crosses
            from tradingmachine.orders.plan_parts import together_part

            part = together_part.TogetherPart(
                children=[
                    order_part.OrderPart(
                        trigger=price_crosses.PriceCrosses(level=995.0),
                    ),
                    order_part.OrderPart(
                        trigger=price_crosses.PriceCrosses(level=990.0),
                    ),
                ],
                group_margin=False,
                done_when="any",
            )
            print(part.document())
            ```
        """
        child_documents = []
        for child in self.children:
            child_documents.append(child.document())
        settings = {
            "children": child_documents,
        }
        if self.group_margin is not None:
            settings["group_margin"] = self.group_margin
        if self.hedge_benefit:
            settings["hedge_benefit"] = True
        if self.done_when is not None:
            settings["done_when"] = self.done_when
        return {
            "together": settings,
        }
