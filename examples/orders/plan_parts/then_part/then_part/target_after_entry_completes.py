"""Build an entry whose profit target is placed only once the entry is done, and which stops buying once the target fills.

The program builds a then join with an `on_complete` child, a protecting limit 2% above an entry at 1000, and sets `cancel_first_on_child_fill`, so a fill on the target cancels whatever of the entry is still working. It then nests that join as the first plan of another, whose child is a time exit at ten past three, to show that joins can hold joins. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/then_part/then_part/target_after_entry_completes.py
"""

import json

from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part
from tradingmachine.orders.plan_parts import time_at


class TargetAfterEntry:
    """An entry, a target placed once the entry is done, and an optional time exit after both.

    Attributes:
        entry_price: The float price in rupees the entry is assumed to buy at.
    """

    def __init__(self):
        """Sets the entry price the target is worked out from.

        Raises:
            Nothing.
        """
        self.entry_price = 1000.0

    def target_join(self) -> then_part.ThenPart:
        """Builds the entry and its target.

        Returns:
            The tradingmachine.orders.plan_parts.then_part.ThenPart joining them.

        Raises:
            Nothing.
        """
        target_price = round(self.entry_price * 1.02, 2)
        return then_part.ThenPart(
            first=order_part.OrderPart(),
            on_complete=order_part.OrderPart(
                side="protect",
                pricing=fixed_pricing.FixedPricing(
                    price=target_price,
                    order_type="LIMIT",
                ),
            ),
            cancel_first_on_child_fill=True,
        )

    def nested_join(self) -> then_part.ThenPart:
        """Builds a join whose first plan is the target join and whose child exits at ten past three.

        Returns:
            The tradingmachine.orders.plan_parts.then_part.ThenPart holding the target join.

        Raises:
            Nothing.
        """
        return then_part.ThenPart(
            first=self.target_join(),
            on_complete=order_part.OrderPart(
                side="protect",
                trigger=time_at.TimeAt("15:10"),
                pricing=fixed_pricing.FixedPricing(order_type="MARKET"),
            ),
        )

    def run(self) -> None:
        """Prints both joins' objects.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print("Entry, then a target once the entry is done:")
        print(json.dumps(self.target_join().document(), indent=2))
        print("The same, nested inside a join that ends with a time exit:")
        print(json.dumps(self.nested_join().document(), indent=2))


if __name__ == "__main__":
    TargetAfterEntry().run()
