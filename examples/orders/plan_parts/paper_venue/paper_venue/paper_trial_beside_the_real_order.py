"""Build the same held limit order three ways: for real, on paper written out, and on paper through the `virtual_limit` preset.

The real order waits on a `limit_marketable` trigger and is sent once the other side of the book reaches its price. Adding a `PaperVenue` is the only change needed to trial it on paper. The `virtual_limit` preset with `paper` set expands to the same trigger and venue inside UBI. The program prints all three. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/paper_venue/paper_venue/paper_trial_beside_the_real_order.py
"""

import json

from tradingmachine.orders.plan_parts import limit_marketable
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import paper_venue
from tradingmachine.orders.plan_parts import preset


class PaperTrial:
    """One held limit order, for real and on paper.

    Attributes:
        versions: The dict mapping a str description to the order_part.OrderPart built that way.
    """

    def __init__(self):
        """Builds the three versions.

        Raises:
            Nothing.
        """
        self.versions = {
            "for real": order_part.OrderPart(
                trigger=limit_marketable.LimitMarketable(),
            ),
            "on paper, written out": order_part.OrderPart(
                trigger=limit_marketable.LimitMarketable(),
                venue=paper_venue.PaperVenue(),
            ),
            "on paper, through the preset": order_part.OrderPart(
                presets=[
                    preset.Preset("virtual_limit", paper=True),
                ],
            ),
        }

    def run(self) -> None:
        """Prints each version.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for description, part in self.versions.items():
            print(f"The held limit order {description}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    PaperTrial().run()
