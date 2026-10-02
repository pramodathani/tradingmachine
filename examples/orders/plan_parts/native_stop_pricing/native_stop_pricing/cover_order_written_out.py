"""Build a cover order by hand: an entry whose every fill gets a stop resting at the broker.

This is what the `cover` preset stands for, written out as a then join. The program builds the entry, then a protecting order priced by a native stop at 990 with its limit at 988, sized to each fill, and prints it beside the preset form. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/native_stop_pricing/native_stop_pricing/cover_order_written_out.py
"""

import json

from tradingmachine.orders.plan_parts import native_stop_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import preset
from tradingmachine.orders.plan_parts import then_part


class CoverByHand:
    """A cover order written as a then join beside the preset that stands for it.

    Attributes:
        stop_price: The float trigger of the stop in rupees.
        stop_limit_price: The float limit of the stop in rupees.
    """

    def __init__(self):
        """Sets the stop's prices.

        Raises:
            Nothing.
        """
        self.stop_price = 990.0
        self.stop_limit_price = 988.0

    def run(self) -> None:
        """Prints the written-out cover order and the preset form.

        Returns:
            None.

        Raises:
            Nothing.
        """
        by_hand = then_part.ThenPart(
            first=order_part.OrderPart(),
            each_fill=order_part.OrderPart(
                side="protect",
                pricing=native_stop_pricing.NativeStopPricing(
                    trigger_price=self.stop_price,
                    limit_price=self.stop_limit_price,
                ),
            ),
        )
        by_preset = order_part.OrderPart(
            presets=[
                preset.Preset(
                    "cover",
                    stop_price=self.stop_price,
                    stop_limit_price=self.stop_limit_price,
                ),
            ],
        )
        print("Written out as a then join:")
        print(json.dumps(by_hand.document(), indent=2))
        print("The same order as a preset:")
        print(json.dumps(by_preset.document(), indent=2))


if __name__ == "__main__":
    CoverByHand().run()
