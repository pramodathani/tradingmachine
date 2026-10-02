"""Build a ladder of five buy limits under Vodafone Idea's price, where every rung that fills is protected by its own stop.

The program reads the share's last price and ladders a buy from 1% to 5% below it. The using join turns each rung into a whole plan, and `each_piece` names the `cover` preset, a then join of the rung and a native stop sized to its fills, so each rung's fills are protected by a stop 2% below the lowest rung. Neither the order nor `each_piece` takes a pricing, because the ladder prices each rung itself. It prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/using_part/using_part/ladder_rungs_each_with_a_stop.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import ladder_execution
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import preset
from tradingmachine.orders.plan_parts import using_part


class StoppedLadder:
    """A five-rung buy ladder whose every rung carries its own stop.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        rungs: The int number of rungs.
    """

    def __init__(self):
        """Looks the share up.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.rungs = 5

    def run(self) -> None:
        """Prints the plan.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        lowest_rung = round(last_price * 0.95, 2)
        stop_price = round(lowest_rung * 0.98, 2)
        plan = using_part.UsingPart(
            order=order_part.OrderPart(
                quantity=500,
                execution=ladder_execution.LadderExecution(
                    from_price=round(last_price * 0.99, 2),
                    to_price=lowest_rung,
                    steps=self.rungs,
                ),
            ),
            each_piece=order_part.OrderPart(
                presets=[
                    preset.Preset(
                        "cover",
                        stop_price=stop_price,
                        stop_limit_price=round(stop_price - 0.05, 2),
                    ),
                ],
            ),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    StoppedLadder().run()
