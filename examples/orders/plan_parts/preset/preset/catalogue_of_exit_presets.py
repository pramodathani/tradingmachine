"""Print the preset objects for four ways of getting out of a position, each named after an existing synthetic order type.

The program builds `trailing_stop`, `cover`, `hidden_stop` and `oto` presets with typical settings for a position bought near 1000, and prints the name and settings object of each, which is what goes into an order's `presets` list. A preset's settings are those of the type it is named after. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/preset/preset/catalogue_of_exit_presets.py
"""

import json

from tradingmachine.orders.plan_parts import preset


class ExitPresetCatalogue:
    """A catalogue of exit presets with a description of each.

    Attributes:
        entries: The list of tuples (description, preset), where description is a str and preset is a tradingmachine.orders.plan_parts.preset.Preset.
    """

    def __init__(self):
        """Builds the presets.

        Raises:
            Nothing.
        """
        self.entries = [
            (
                "a stop that trails 5 rupees behind the best price",
                preset.Preset(
                    "trailing_stop",
                    trail_points=5.0,
                    stop_limit_offset=1.0,
                ),
            ),
            (
                "a compulsory stop placed with every fill",
                preset.Preset(
                    "cover",
                    stop_price=990.0,
                    stop_limit_price=988.0,
                ),
            ),
            (
                "a stop kept inside UBI with a real backstop behind it",
                preset.Preset(
                    "hidden_stop",
                    trigger_price=992.0,
                    backstop_price=985.0,
                    backstop_limit_price=983.0,
                ),
            ),
            (
                "a limit sell sized to whatever the entry filled",
                preset.Preset(
                    "oto",
                    then={
                        "transaction_type": "SELL",
                        "order_type": "LIMIT",
                        "price": 1015.0,
                    },
                ),
            ),
        ]

    def run(self) -> None:
        """Prints each preset's description, name and object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for description, exit_preset in self.entries:
            print(f"{exit_preset.name}: {description}")
            print(json.dumps(exit_preset.document(), indent=2))


if __name__ == "__main__":
    ExitPresetCatalogue().run()
