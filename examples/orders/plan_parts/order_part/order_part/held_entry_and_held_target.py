"""Preview a plan whose entry and profit target are both held until the market reaches them, and one whose entry rests at the broker.

The program reads Vodafone Idea's last price and builds a buy 3% below it, followed on each fill by a sell 3% above it. UBI holds the entry by default, but a profit target is a follow-on order that rests at the broker unless its own order asks to be held, so the target's `OrderPart` gives `hold_limits=True`. A second plan gives its entry `hold_limits=False`, so the entry would rest at the broker at once. Both are sent as dry runs, so UBI checks them and answers with the plan it would run, and nothing is recorded or sent.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/order_part/order_part/held_entry_and_held_target.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders import plan
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part


class HeldEntryAndTarget:
    """Two previews of an entry with a profit target, differing only in what UBI holds.

    Attributes:
        share: The tradingmachine.assets.equities.Equity both plans trade.
        entry_price: The float price in rupees of the buy, 3% below the last price.
        target_price: The float price in rupees of the sell, 3% above the last price.
    """

    def __init__(self):
        """Looks the share up and works out both prices from its last price.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not look the share up or quote it.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        last_price = self.share.last_price
        self.entry_price = round(last_price * 0.97, 2)
        self.target_price = round(last_price * 1.03, 2)

    def plan_order(self, entry_hold_limits: bool | None) -> plan.PlanOrder:
        """Builds the entry and its target as a dry-run plan.

        Args:
            entry_hold_limits: A bool or None given to the entry's `OrderPart` as its `hold_limits`.

        Returns:
            A tradingmachine.orders.plan.PlanOrder that buys at the entry price and sells each fill at the target price.

        Raises:
            Nothing.
        """
        target = order_part.OrderPart(
            side="protect",
            pricing=fixed_pricing.FixedPricing(price=self.target_price),
            hold_limits=True,
        )
        return plan.PlanOrder(
            self.share,
            transaction_type="buy",
            product="mis",
            order_type="limit",
            quantity=1,
            price=self.entry_price,
            plan=then_part.ThenPart(
                first=order_part.OrderPart(hold_limits=entry_hold_limits),
                each_fill=target,
            ),
            dry_run=True,
        )

    def run(self) -> None:
        """Previews both plans and prints what UBI would hold.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a plan or could not be reached.
        """
        print(f"Entry at {self.entry_price}, target at {self.target_price}")
        for description, entry_hold_limits in [
            ("entry held by default", None),
            ("entry resting at the broker", False),
        ]:
            order = self.plan_order(entry_hold_limits)
            print(f"Plan with the {description}:")
            print(json.dumps(order.synthetic["plan"], indent=2))
            answer = order.place()
            print(json.dumps(answer.get("plan"), indent=2, default=str))


if __name__ == "__main__":
    HeldEntryAndTarget().run()
