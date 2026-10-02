"""The `sequence` join of a plan: two to twenty-five plans run one after another.

Each child starts only once the one before it is done, whether it filled or ended, so a sequence is how a plan waits for one order to finish before the next is even considered. A sequence join cannot be a `then` join's child, because that child is sized to the first plan's fills.

Typical usage example:

  part = sequence_part.SequencePart(
      children=[
          order_part.OrderPart(trigger=time_at.TimeAt("10:00")),
          order_part.OrderPart(trigger=time_at.TimeAt("14:00")),
      ],
  )
  document = part.document()
"""

from collections.abc import Sequence

from tradingmachine.orders.plan_parts import plan_part


class SequencePart(plan_part.PlanPart):
    """Several plans run one after another, each starting once the one before is done.

    Attributes:
        children: The list of plan_part.PlanPart nodes, in the order they run.
    """

    def __init__(
        self,
        *,
        children: Sequence[plan_part.PlanPart],
    ):
        """Initialises the join with its children.

        Args:
            children: A sequence of two to twenty-five plan_part.PlanPart nodes, each an `OrderPart` or another join, in the order they run.

        Raises:
            Nothing.
        """
        self.children = list(children)

    def document(self) -> dict:
        """Builds the `sequence` node UBI reads.

        Returns:
            A dict with the single key `sequence`, whose value holds `children`.

        Raises:
            Nothing.

        Examples:
            Print two buys where the second is considered only once the first is done:

            ```python
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import price_crosses
            from tradingmachine.orders.plan_parts import sequence_part

            part = sequence_part.SequencePart(
                children=[
                    order_part.OrderPart(
                        trigger=price_crosses.PriceCrosses(level=995.0),
                    ),
                    order_part.OrderPart(
                        trigger=price_crosses.PriceCrosses(level=990.0),
                    ),
                ],
            )
            print(part.document())
            ```

            Print an entry with its protecting stop, followed once both are done by a second entry later in the day:

            ```python
            from tradingmachine.orders.plan_parts import native_stop_pricing
            from tradingmachine.orders.plan_parts import order_part
            from tradingmachine.orders.plan_parts import sequence_part
            from tradingmachine.orders.plan_parts import then_part
            from tradingmachine.orders.plan_parts import time_at

            part = sequence_part.SequencePart(
                children=[
                    then_part.ThenPart(
                        first=order_part.OrderPart(),
                        each_fill=order_part.OrderPart(
                            side="protect",
                            pricing=native_stop_pricing.NativeStopPricing(
                                trigger_price=990.0,
                                limit_price=988.0,
                            ),
                        ),
                    ),
                    order_part.OrderPart(trigger=time_at.TimeAt("14:00")),
                ],
            )
            print(part.document())
            ```
        """
        child_documents = []
        for child in self.children:
            child_documents.append(child.document())
        return {
            "sequence": {
                "children": child_documents,
            },
        }
