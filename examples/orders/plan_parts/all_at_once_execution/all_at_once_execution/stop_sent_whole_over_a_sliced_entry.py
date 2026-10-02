"""Build an entry sent in TWAP slices whose protective stop is sent whole.

The program builds a then join whose first order buys in six TWAP slices over half an hour and whose `each_fill` order protects every fill with a native stop. The stop states `AllAtOnceExecution` explicitly, because a resting stop protects the whole position at once and UBI refuses to slice it. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/all_at_once_execution/all_at_once_execution/stop_sent_whole_over_a_sliced_entry.py
"""

import json

from tradingmachine.orders.plan_parts import all_at_once_execution
from tradingmachine.orders.plan_parts import native_stop_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part
from tradingmachine.orders.plan_parts import twap_execution


class SlicedEntryWholeStop:
    """A sliced entry protected by one stop that grows with every fill.

    Attributes:
        join: The tradingmachine.orders.plan_parts.then_part.ThenPart the program prints.
    """

    def __init__(self):
        """Builds the then join.

        Raises:
            Nothing.
        """
        self.join = then_part.ThenPart(
            first=order_part.OrderPart(
                execution=twap_execution.TwapExecution(
                    slices=6,
                    over_minutes=30,
                ),
            ),
            each_fill=order_part.OrderPart(
                side="protect",
                pricing=native_stop_pricing.NativeStopPricing(
                    trigger_price=11.9,
                    limit_price=11.85,
                ),
                execution=all_at_once_execution.AllAtOnceExecution(),
            ),
        )

    def run(self) -> None:
        """Prints the join's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(json.dumps(self.join.document(), indent=2))
        print(
            "The entry goes in six slices; the stop is one order resized with every fill."
        )


if __name__ == "__main__":
    SlicedEntryWholeStop().run()
