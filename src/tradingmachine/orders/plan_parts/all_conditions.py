"""The `all` trigger of a plan: a group of conditions that holds when every one of them holds.

Typical usage example:

  condition = all_conditions.AllConditions(
      [
          time_after.TimeAfter("10:00"),
          price_crosses.PriceCrosses(level=995.0),
      ]
  )
  document = condition.document()
"""

from collections.abc import Sequence

from tradingmachine.orders.plan_parts import plan_part


class AllConditions(plan_part.PlanPart):
    """A group of trigger conditions that must all hold.

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
        """Builds the `all` group UBI reads.

        Returns:
            A dict with the single key `all`, whose value is the list of the conditions' objects.

        Raises:
            Nothing.

        Examples:
            Print a touch at 995 that counts only after ten in the morning:

            ```python
            from tradingmachine.orders.plan_parts import all_conditions
            from tradingmachine.orders.plan_parts import price_crosses
            from tradingmachine.orders.plan_parts import time_after

            condition = all_conditions.AllConditions(
                [
                    time_after.TimeAfter("10:00"),
                    price_crosses.PriceCrosses(level=995.0),
                ]
            )
            print(condition.document())
            ```

            Print a group holding another group, a touch on either the bid or the last price:

            ```python
            from tradingmachine.orders.plan_parts import all_conditions
            from tradingmachine.orders.plan_parts import any_condition
            from tradingmachine.orders.plan_parts import price_crosses
            from tradingmachine.orders.plan_parts import time_before

            condition = all_conditions.AllConditions(
                [
                    time_before.TimeBefore("15:00"),
                    any_condition.AnyCondition(
                        [
                            price_crosses.PriceCrosses(level=995.0, field="bid"),
                            price_crosses.PriceCrosses(level=995.0, field="last"),
                        ]
                    ),
                ]
            )
            print(condition.document())
            ```
        """
        condition_documents = []
        for condition in self.conditions:
            condition_documents.append(condition.document())
        return {
            "all": condition_documents,
        }
