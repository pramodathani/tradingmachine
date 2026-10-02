"""Compare a hedge sized by an option's delta with one sized by a fixed ratio of the option's fills.

Both plans buy an option and hedge each fill on another instrument. The first uses a `parent_fill_delta` quantity, which needs the `against_delta` side and lets UBI choose the hedge's direction from the option type, selling against a call and buying against a put. The second uses a `parent_fill` quantity with a fixed ratio of one half and states the hedge's side itself. The program prints both so the difference in the documents is plain to see. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/parent_fill_delta_quantity/parent_fill_delta_quantity/compare_delta_and_plain_hedges.py
"""

import json

from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import parent_fill_delta_quantity
from tradingmachine.orders.plan_parts import parent_fill_quantity
from tradingmachine.orders.plan_parts import then_part


class HedgeComparison:
    """Two hedges of the same option entry, one by delta and one by a fixed ratio.

    Attributes:
        volatility_percent: The float volatility in percent the delta is worked out at.
    """

    def __init__(self):
        """Sets the volatility.

        Raises:
            Nothing.
        """
        self.volatility_percent = 15.0

    def run(self) -> None:
        """Prints both plans.

        Returns:
            None.

        Raises:
            Nothing.
        """
        by_delta = then_part.ThenPart(
            first=order_part.OrderPart(),
            each_fill=order_part.OrderPart(
                side="against_delta",
                quantity=parent_fill_delta_quantity.ParentFillDeltaQuantity(
                    volatility=self.volatility_percent,
                ),
            ),
        )
        by_ratio = then_part.ThenPart(
            first=order_part.OrderPart(),
            each_fill=order_part.OrderPart(
                transaction_type="sell",
                quantity=parent_fill_quantity.ParentFillQuantity(ratio=0.5),
            ),
        )
        print("Hedged by the option's delta:")
        print(json.dumps(by_delta.document(), indent=2))
        print("Hedged by a fixed half of each fill:")
        print(json.dumps(by_ratio.document(), indent=2))


if __name__ == "__main__":
    HedgeComparison().run()
