"""Build an entry that is given up once the day's loss across the account reaches a limit.

The program holds a dip-buying entry on a touch, and gives the entry a lifetime that ends it, cancelling whatever still rests, once `day_pnl` falls to minus 5,000 rupees. The account figure is read by UBI's engine across every broker. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/account_condition/account_condition/stop_trading_after_a_bad_day.py
"""

import json

from tradingmachine.orders.plan_parts import account_condition
from tradingmachine.orders.plan_parts import lifetime
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses


class BadDayCutoff:
    """A dip entry that ends once the day's loss reaches a limit.

    Attributes:
        loss_limit: The float day's profit, negative for a loss, at which the entry ends.
        entry_level: The float price the entry waits for.
    """

    def __init__(self):
        """Sets the loss limit and the entry level.

        Raises:
            Nothing.
        """
        self.loss_limit = -5000.0
        self.entry_level = 995.0

    def run(self) -> None:
        """Prints the entry's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        cutoff = account_condition.AccountCondition(
            field="day_pnl",
            level=self.loss_limit,
            direction="at_or_below",
        )
        part = order_part.OrderPart(
            trigger=price_crosses.PriceCrosses(level=self.entry_level),
            lifetime=lifetime.Lifetime(when=cutoff),
        )
        print(f"The entry ends once the day's profit is {self.loss_limit}:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    BadDayCutoff().run()
