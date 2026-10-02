"""The `any` trigger of a plan: a group of conditions that holds when any one of them holds.

Typical usage example:

  condition = any_condition.AnyCondition(
      [
          price_crosses.PriceCrosses(level=990.0, direction="at_or_below"),
          time_at.TimeAt("15:10"),
      ]
  )
  document = condition.document()
"""

from collections.abc import Sequence

from tradingmachine.orders.plan_parts import plan_part


class AnyCondition(plan_part.PlanPart):
    """A group of trigger conditions of which any one is enough.

    Attributes:
        conditions: The list of plan_part.PlanPart conditions in the group.
    """

    def __init__(
        self,
        conditions: Sequence[plan_part.PlanPart],
    ):
        """Initialises the group with its conditions.

        Args:
            conditions: A sequence of plan_part.PlanPart conditions, which may include other groups.

        Raises:
            Nothing.
        """
        self.conditions = list(conditions)

    def document(self) -> dict:
        """Builds the `any` group UBI reads.

        Returns:
            A dict with the single key `any`, whose value is the list of the conditions' objects.

        Raises:
            Nothing.

        Examples:
            Print an exit that fires on a fall to 990 or at ten past three, whichever comes first:

            ```python
            from tradingmachine.orders.plan_parts import any_condition
            from tradingmachine.orders.plan_parts import price_crosses
            from tradingmachine.orders.plan_parts import time_at

            condition = any_condition.AnyCondition(
                [
                    price_crosses.PriceCrosses(level=990.0, direction="at_or_below"),
                    time_at.TimeAt("15:10"),
                ]
            )
            print(condition.document())
            ```

            Print an exit that fires on a pullback of five rupees or a fall to 990:

            ```python
            from tradingmachine.orders.plan_parts import any_condition
            from tradingmachine.orders.plan_parts import price_crosses
            from tradingmachine.orders.plan_parts import trails

            condition = any_condition.AnyCondition(
                [
                    trails.Trails(points=5.0),
                    price_crosses.PriceCrosses(level=990.0, direction="at_or_below"),
                ]
            )
            print(condition.document())
            ```
        """
        condition_documents = []
        for condition in self.conditions:
            condition_documents.append(condition.document())
        return {
            "any": condition_documents,
        }
