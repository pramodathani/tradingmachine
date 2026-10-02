"""The `account` trigger of a plan: a figure from the whole account reaching a level, rather than a price.

The figure is `available_balance`, the free margin across every broker; `day_pnl`, the day's realized and unrealized profit across every broker; or `open_positions`, how many net positions are open. All three settings are required, the direction too, because nothing about an order says which way an account figure should move. The condition reads no quotes, so UBI checks it once a second on the clock.

Typical usage example:

  condition = account_condition.AccountCondition(
      field="day_pnl",
      level=-5000.0,
      direction="at_or_below",
  )
  document = condition.document()
"""

from tradingmachine.orders.plan_parts import plan_part


class AccountCondition(plan_part.PlanPart):
    """A condition that holds when a figure from the account is at or past a level.

    Attributes:
        field: The str figure, `available_balance`, `day_pnl` or `open_positions`.
        level: The float level the figure is compared with, in rupees or, for `open_positions`, a count.
        direction: The str direction, `at_or_above` or `at_or_below`.
    """

    def __init__(
        self,
        *,
        field: str,
        level: float,
        direction: str,
    ):
        """Initialises the condition with its figure, level and direction.

        Args:
            field: The str figure, `available_balance` for the free margin across every broker, `day_pnl` for the day's realized plus unrealized profit across every broker, or `open_positions` for the count of open net positions.
            level: The float level, in rupees for the two money figures and a count for `open_positions`.
            direction: The str direction, `at_or_above` or `at_or_below`, which is required.

        Raises:
            Nothing.
        """
        self.field = field
        self.level = level
        self.direction = direction

    def document(self) -> dict:
        """Builds the `account` condition UBI reads.

        Returns:
            A dict with the single key `account`, whose value holds `field`, `level` and `direction`.

        Raises:
            Nothing.

        Examples:
            Print a condition that holds once the day's loss reaches 5,000 rupees:

            ```python
            from tradingmachine.orders.plan_parts import account_condition

            condition = account_condition.AccountCondition(
                field="day_pnl",
                level=-5000.0,
                direction="at_or_below",
            )
            print(condition.document())
            ```

            Print an entry held until the free margin is back at or above 50,000 rupees:

            ```python
            from tradingmachine.orders.plan_parts import account_condition
            from tradingmachine.orders.plan_parts import order_part

            part = order_part.OrderPart(
                trigger=account_condition.AccountCondition(
                    field="available_balance",
                    level=50000.0,
                    direction="at_or_above",
                ),
            )
            print(part.document())
            ```

            Print a condition that holds once no position is open any more:

            ```python
            from tradingmachine.orders.plan_parts import account_condition

            condition = account_condition.AccountCondition(
                field="open_positions",
                level=0,
                direction="at_or_below",
            )
            print(condition.document())
            ```
        """
        return {
            "account": {
                "field": self.field,
                "level": self.level,
                "direction": self.direction,
            },
        }
