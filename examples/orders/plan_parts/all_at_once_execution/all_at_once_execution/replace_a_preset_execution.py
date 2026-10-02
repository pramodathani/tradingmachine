"""Build an order whose preset slices it, then send it whole instead.

The program builds two orders from UBI's `twap` preset: the first as the preset gives it, and the second with `AllAtOnceExecution` as its own execution, which UBI applies after the preset and so replaces the slicing with a warning. Comparing the two shows how an order's own slot values override a preset. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/all_at_once_execution/all_at_once_execution/replace_a_preset_execution.py
"""

import json

from tradingmachine.orders.plan_parts import all_at_once_execution
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import preset


class PresetExecutionReplaced:
    """Two orders built from the TWAP preset, one sliced and one sent whole.

    Attributes:
        orders: The dict of str descriptions to tradingmachine.orders.plan_parts.order_part.OrderPart objects the program prints.
    """

    def __init__(self):
        """Builds both orders.

        Raises:
            Nothing.
        """
        self.orders = {
            "as the preset gives it": order_part.OrderPart(
                presets=[
                    preset.Preset("twap", slices=4, over_minutes=20),
                ],
            ),
            "sent whole": order_part.OrderPart(
                presets=[
                    preset.Preset("twap", slices=4, over_minutes=20),
                ],
                execution=all_at_once_execution.AllAtOnceExecution(),
            ),
        }

    def run(self) -> None:
        """Prints both orders' objects.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for description, part in self.orders.items():
            print(f"The TWAP preset {description}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    PresetExecutionReplaced().run()
