"""Build a TWAP buy of Vodafone Idea in four slices over an hour, where every slice carries its own bracket.

The program reads the share's last price and splits a buy with a `TwapExecution`. The using join turns each of the four slices into a whole plan of its own, and `each_piece` names the `bracket` preset, so every slice is followed by a stop 3% below and a target 3% above the price now, sized to that slice's fills. A timed execution in a using join gives `over_minutes`, because UBI spaces the pieces by its interval. It prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/using_part/using_part/twap_slices_each_with_a_bracket.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import preset
from tradingmachine.orders.plan_parts import twap_execution
from tradingmachine.orders.plan_parts import using_part


class BracketedTwapSlices:
    """A TWAP buy whose every slice is bracketed.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
    """

    def __init__(self):
        """Looks the share up.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

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
        stop_price = round(last_price * 0.97, 2)
        plan = using_part.UsingPart(
            order=order_part.OrderPart(
                execution=twap_execution.TwapExecution(
                    slices=4,
                    over_minutes=60,
                ),
            ),
            each_piece=order_part.OrderPart(
                presets=[
                    preset.Preset(
                        "bracket",
                        stop_price=stop_price,
                        stop_limit_price=round(stop_price - 0.05, 2),
                        target_price=round(last_price * 1.03, 2),
                    ),
                ],
            ),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    BracketedTwapSlices().run()
