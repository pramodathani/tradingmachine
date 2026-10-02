"""Build the two ways a resting stop may be sent, and one way UBI refuses.

A resting stop protects the whole position at once, so UBI lets its order be sent only whole, by `AllAtOnceExecution`, or renewed whole each morning, by `DailyExecution`; any execution that splits it into pieces is refused with `stop_not_sliced`. The program builds the same stop three ways, the third with a TWAP, and prints each document with whether UBI accepts it. It only builds the documents, so the refusal it reports is UBI's documented rule rather than an answer from UBI. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/daily_execution/daily_execution/sliced_stop_refused.py
"""

import json

from tradingmachine.orders.plan_parts import all_at_once_execution
from tradingmachine.orders.plan_parts import daily_execution
from tradingmachine.orders.plan_parts import native_stop_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import twap_execution


class StopExecutions:
    """The same protecting stop under three executions.

    Attributes:
        executions: The list of tuples (description, execution, accepted), where description is a str, execution a tradingmachine.orders.plan_parts.plan_part.PlanPart and accepted a bool saying whether UBI takes it for a stop.
    """

    def __init__(self):
        """Builds the three executions.

        Raises:
            Nothing.
        """
        self.executions = [
            (
                "sent whole",
                all_at_once_execution.AllAtOnceExecution(),
                True,
            ),
            (
                "renewed at 09:30 each trading day",
                daily_execution.DailyExecution(arm_at="09:30"),
                True,
            ),
            (
                "split into a TWAP",
                twap_execution.TwapExecution(slices=4, over_minutes=20),
                False,
            ),
        ]

    def run(self) -> None:
        """Prints each stop's object and whether UBI accepts it.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for description, execution, accepted in self.executions:
            part = order_part.OrderPart(
                side="protect",
                pricing=native_stop_pricing.NativeStopPricing(
                    trigger_price=950.0,
                    limit_price=948.0,
                ),
                execution=execution,
            )
            verdict = "accepted"
            if not accepted:
                verdict = "refused with stop_not_sliced"
            print(f"A stop {description}, {verdict}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    StopExecutions().run()
