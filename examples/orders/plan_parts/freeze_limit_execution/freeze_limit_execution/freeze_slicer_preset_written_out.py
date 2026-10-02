"""Build the same large order from UBI's `freeze_slicer` preset and written out with `FreezeLimitExecution`.

UBI's `freeze_slicer` preset is nothing more than the `freeze_limit` execution, so the two documents the program prints ask for the same thing. Neither nests with another execution, so an order above the freeze quantity that should also be spread over time cannot be built. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/freeze_limit_execution/freeze_limit_execution/freeze_slicer_preset_written_out.py
"""

import json

from tradingmachine.orders.plan_parts import freeze_limit_execution
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import preset


class FreezeSlicerTwoWays:
    """One large order described from the preset and from the execution.

    Attributes:
        orders: The dict of str descriptions to tradingmachine.orders.plan_parts.order_part.OrderPart objects the program prints.
    """

    def __init__(self):
        """Builds both orders.

        Raises:
            Nothing.
        """
        self.orders = {
            "from the freeze_slicer preset": order_part.OrderPart(
                quantity=3600,
                presets=[
                    preset.Preset("freeze_slicer"),
                ],
            ),
            "with FreezeLimitExecution": order_part.OrderPart(
                quantity=3600,
                execution=freeze_limit_execution.FreezeLimitExecution(),
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
            print(f"A large order {description}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    FreezeSlicerTwoWays().run()
