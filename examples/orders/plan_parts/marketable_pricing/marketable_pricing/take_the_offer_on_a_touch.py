"""Build a market-if-touched entry by hand: wait for a dip, then take the offer with a marketable limit.

This is what the `market_if_touched` preset stands for, written out as slot values. The program builds an order that waits for the price to fall to 995 and is then sent two ticks past the best offer, so it fills at once without the risk of a plain market order in an empty book. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/marketable_pricing/marketable_pricing/take_the_offer_on_a_touch.py
"""

import json

from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import preset
from tradingmachine.orders.plan_parts import price_crosses


class TouchEntryByHand:
    """A market-if-touched entry written as slot values beside the preset that stands for it.

    Attributes:
        touch_level: The float level in rupees the price must fall to.
    """

    def __init__(self):
        """Sets the level.

        Raises:
            Nothing.
        """
        self.touch_level = 995.0

    def run(self) -> None:
        """Prints the slot-value entry and the preset entry.

        Returns:
            None.

        Raises:
            Nothing.
        """
        by_hand = order_part.OrderPart(
            trigger=price_crosses.PriceCrosses(level=self.touch_level),
            pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
        )
        by_preset = order_part.OrderPart(
            presets=[
                preset.Preset("market_if_touched", trigger_price=self.touch_level),
            ],
        )
        print("Written out as slot values:")
        print(json.dumps(by_hand.document(), indent=2))
        print("The same entry as a preset:")
        print(json.dumps(by_preset.document(), indent=2))


if __name__ == "__main__":
    TouchEntryByHand().run()
