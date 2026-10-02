"""Build an entry from two presets: wait until ten in the morning, and then for the price to dip to a level.

The program combines the `scheduled` and `market_if_touched` presets in one order, which UBI joins so that both must hold, and adds its own marketable pricing with a wider buffer, which replaces the preset's. It prints the order object, and then a second order with the same presets but no pricing of its own, to show the difference. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/order_part/order_part/dip_entry_from_presets.py
"""

import json

from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import preset


class DipEntry:
    """Two entries built from the same presets, one with pricing of its own.

    Attributes:
        presets: The list of tradingmachine.orders.plan_parts.preset.Preset both entries use.
    """

    def __init__(self):
        """Builds the presets.

        Raises:
            Nothing.
        """
        self.presets = [
            preset.Preset("scheduled", at_time="10:00"),
            preset.Preset("market_if_touched", trigger_price=995.0),
        ]

    def entries(self) -> dict:
        """Builds the two entries.

        Returns:
            A dict of a str description to the tradingmachine.orders.plan_parts.order_part.OrderPart it describes.

        Raises:
            Nothing.
        """
        return {
            "presets only": order_part.OrderPart(presets=self.presets),
            "presets with a five-tick buffer": order_part.OrderPart(
                presets=self.presets,
                pricing=marketable_pricing.MarketablePricing(buffer_ticks=5),
            ),
        }

    def run(self) -> None:
        """Prints both entries' objects.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for description, part in self.entries().items():
            print(f"Entry with {description}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    DipEntry().run()
