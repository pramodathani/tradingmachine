"""Build an entry whose position is taken off on a ladder of targets once it has filled.

The program builds a then join: the template's own order first, and under `on_complete` a protecting order sent as a ladder of four limit orders from 1020 to 1050, so the position is sold in four equal parts as the price rises. The ladder needs no pricing, because its rungs set the prices. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/ladder_execution/ladder_execution/scale_out_after_entry.py
"""

import json

from tradingmachine.orders.plan_parts import ladder_execution
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part


class LadderedExit:
    """An entry followed by a four-rung ladder of targets.

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
            on_complete=order_part.OrderPart(
                side="protect",
                execution=ladder_execution.LadderExecution(
                    from_price=1020.0,
                    to_price=1050.0,
                    steps=4,
                ),
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


if __name__ == "__main__":
    LadderedExit().run()
