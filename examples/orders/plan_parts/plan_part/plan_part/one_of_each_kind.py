"""Build one part of every kind a plan is made of and show that each is a PlanPart.

The program builds a node, a preset, a trigger condition and a pricing rule, checks that each is a `PlanPart`, and prints the single UBI key each one's object holds. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/plan_part/plan_part/one_of_each_kind.py
"""

from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import plan_part
from tradingmachine.orders.plan_parts import preset
from tradingmachine.orders.plan_parts import price_crosses


class PartKindReport:
    """A report of the UBI key each kind of plan part stands for.

    Attributes:
        parts: The dict of a str kind name to the plan_part.PlanPart of that kind.
    """

    def __init__(self):
        """Builds one part of each kind.

        Raises:
            Nothing.
        """
        self.parts = {
            "node": order_part.OrderPart(),
            "preset": preset.Preset("scheduled", at_time="10:00"),
            "trigger": price_crosses.PriceCrosses(level=995.0),
            "pricing": fixed_pricing.FixedPricing(price=1010.0, order_type="LIMIT"),
        }

    def run(self) -> None:
        """Prints each part's kind, class, whether it is a PlanPart and its UBI key.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for kind, part in self.parts.items():
            document = part.document()
            is_part = isinstance(part, plan_part.PlanPart)
            for key in document:
                print(f"{kind:8} {type(part).__name__:14} PlanPart={is_part} key={key}")


if __name__ == "__main__":
    PartKindReport().run()
