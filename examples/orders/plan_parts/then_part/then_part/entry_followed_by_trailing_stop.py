"""Build an entry whose every fill is protected at once by a trailing stop.

The program builds a then join whose first plan is the template's own order and whose `each_fill` child is a protecting order priced by a stop that trails 2% behind the market. Because the child is sized to what has filled and resized with every fill, a partly filled entry is protected for exactly what was bought. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/then_part/then_part/entry_followed_by_trailing_stop.py
"""

import json

from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part
from tradingmachine.orders.plan_parts import trail_pricing


class TrailedEntry:
    """An entry followed by a trailing stop sized to each fill.

    Attributes:
        join: The tradingmachine.orders.plan_parts.then_part.ThenPart the program prints.
    """

    def __init__(self):
        """Builds the then join.

        Raises:
            Nothing.
        """
        self.join = then_part.ThenPart(
            first=order_part.OrderPart(),
            each_fill=order_part.OrderPart(
                side="protect",
                pricing=trail_pricing.TrailPricing(
                    percent=2.0,
                    limit_offset=0.05,
                ),
            ),
        )

    def run(self) -> None:
        """Prints the join's object and says when its child starts.

        Returns:
            None.

        Raises:
            Nothing.
        """
        document = self.join.document()
        print(json.dumps(document, indent=2))
        if "each_fill" in document["then"]:
            print(
                "The stop starts on the entry's first fill and grows with every fill."
            )


if __name__ == "__main__":
    TrailedEntry().run()
