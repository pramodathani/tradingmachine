"""Build front-loaded orders at three urgencies and show how each shares out 1000 shares.

Each slice of a front-loaded execution is `1 - urgency × 0.5` of the one before, so an urgency of 0 is an even split, UBI's default of 0.5 makes each slice three quarters of the last, and 1 halves every slice. The program builds five slices over half an hour at each urgency, prints the documents, and prints the approximate share of 1000 each slice would take, before UBI rounds them to whole units. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/front_loaded_execution/front_loaded_execution/compare_urgencies.py
"""

import json

from tradingmachine.orders.plan_parts import front_loaded_execution
from tradingmachine.orders.plan_parts import order_part


class UrgencyComparison:
    """Three front-loaded schedules for the same order.

    Attributes:
        quantity: The int quantity shared out in the printed comparison.
        urgencies: The list of float urgencies compared, None standing for UBI's default.
    """

    def __init__(self):
        """Chooses the quantity and the urgencies.

        Raises:
            Nothing.
        """
        self.quantity = 1000
        self.urgencies = [
            0.0,
            None,
            1.0,
        ]

    def run(self) -> None:
        """Prints each order's object and its approximate slice sizes.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for urgency in self.urgencies:
            execution = front_loaded_execution.FrontLoadedExecution(
                slices=5,
                over_minutes=30,
                urgency=urgency,
            )
            part = order_part.OrderPart(quantity=self.quantity, execution=execution)
            print(json.dumps(part.document(), indent=2))
            effective_urgency = 0.5
            if urgency is not None:
                effective_urgency = urgency
            ratio = 1 - effective_urgency * 0.5
            weights = []
            weight = 1.0
            for _ in range(execution.slices):
                weights.append(weight)
                weight = weight * ratio
            total = sum(weights)
            sizes = []
            for weight in weights:
                sizes.append(round(self.quantity * weight / total))
            print(f"Urgency {effective_urgency}: slices of about {sizes}")


if __name__ == "__main__":
    UrgencyComparison().run()
