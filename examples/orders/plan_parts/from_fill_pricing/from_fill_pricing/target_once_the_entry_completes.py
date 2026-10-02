"""Build an entry whose single target is sent only once the whole entry has filled, measured from its average fill.

The program builds a Then join for Vodafone Idea with `on_complete`, so the target waits until the buy is done, and prices the target half a rupee above the entry's average fill. The same exit works unchanged after a sale, where UBI places it below the fill instead. It prints the join's object as UBI would read it. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/from_fill_pricing/from_fill_pricing/target_once_the_entry_completes.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import from_fill_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part


class TargetAfterCompletion:
    """A buy of Vodafone Idea followed by a target once it has filled completely.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
    """

    def __init__(self):
        """Looks up the share.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def run(self) -> None:
        """Prints the join's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        part = then_part.ThenPart(
            first=order_part.OrderPart(
                instrument=self.share,
                transaction_type="buy",
                quantity=10,
            ),
            on_complete=order_part.OrderPart(
                side="protect",
                pricing=from_fill_pricing.FromFillPricing(target_distance=0.5),
            ),
        )
        print(f"Buy of {self.share.symbol} with a target half a rupee up:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    TargetAfterCompletion().run()
