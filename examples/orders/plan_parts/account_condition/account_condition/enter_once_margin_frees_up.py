"""Build an entry that waits until the account has free margin again, and has no more than two positions open.

The program joins two `account` conditions with `AllConditions`: the free margin across every broker at or above 50,000 rupees, and the count of open net positions at or below 2. The entry is sent at a marketable limit once both hold. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/account_condition/account_condition/enter_once_margin_frees_up.py
"""

import json

from tradingmachine.orders.plan_parts import account_condition
from tradingmachine.orders.plan_parts import all_conditions
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part


class MarginGatedEntry:
    """An entry held until the account has room for it.

    Attributes:
        minimum_margin: The float free margin in rupees the entry needs.
        most_positions: The int number of open positions allowed before the entry.
    """

    def __init__(self):
        """Sets the margin and position limits.

        Raises:
            Nothing.
        """
        self.minimum_margin = 50000.0
        self.most_positions = 2

    def run(self) -> None:
        """Prints the entry's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        room = all_conditions.AllConditions(
            [
                account_condition.AccountCondition(
                    field="available_balance",
                    level=self.minimum_margin,
                    direction="at_or_above",
                ),
                account_condition.AccountCondition(
                    field="open_positions",
                    level=self.most_positions,
                    direction="at_or_below",
                ),
            ]
        )
        part = order_part.OrderPart(
            trigger=room,
            pricing=marketable_pricing.MarketablePricing(),
        )
        print("The entry waits for margin and a free position slot:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    MarginGatedEntry().run()
