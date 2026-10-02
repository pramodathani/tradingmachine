"""Check a list of plan parts before building a plan, and see that the base class itself describes nothing.

A program that assembles plans from user input can check that every piece it was given is a `PlanPart` whose object holds exactly one key, which is the shape UBI reads. The program checks three good parts, a plain dict that is not a part, and the bare base class, which refuses to describe itself. Nothing is sent to UBI.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/plan_part/plan_part/check_parts_before_sending.py
"""

from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import plan_part
from tradingmachine.orders.plan_parts import time_at
from tradingmachine.orders.plan_parts import trails


class PartChecker:
    """A checker that reports which candidate pieces can go into a plan.

    Attributes:
        candidates: The list of objects to check, some of them not usable parts.
    """

    def __init__(self):
        """Builds the pieces to check.

        Raises:
            Nothing.
        """
        self.candidates = [
            time_at.TimeAt("10:00"),
            trails.Trails(points=5.0),
            marketable_pricing.MarketablePricing(buffer_ticks=2),
            {
                "price_crosses": {
                    "level": 995.0,
                },
            },
            plan_part.PlanPart(),
        ]

    def verdict(self, candidate: object) -> str:
        """Says whether one piece can go into a plan, and why not when it cannot.

        Args:
            candidate: The object to check.

        Returns:
            A str verdict.

        Raises:
            Nothing.
        """
        if not isinstance(candidate, plan_part.PlanPart):
            return "refused: not a PlanPart, so it cannot be placed in a plan"
        try:
            document = candidate.document()
        except NotImplementedError as error:
            return f"refused: {error}"
        if len(document) != 1:
            return "refused: its object does not hold exactly one key"
        return f"accepted: {document}"

    def run(self) -> None:
        """Prints the verdict on every candidate.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for candidate in self.candidates:
            print(f"{type(candidate).__name__:18} {self.verdict(candidate)}")


if __name__ == "__main__":
    PartChecker().run()
