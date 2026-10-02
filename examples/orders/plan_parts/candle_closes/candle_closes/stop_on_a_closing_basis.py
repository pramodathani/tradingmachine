"""Build a protective stop that leaves only when a fifteen-minute bar closes below a level.

A stop on a touch can be taken out by one wild tick on a thin book. The program reads the last price of NSE IDEA, puts the level five percent below it, and protects the position with a `candle_closes` trigger on fifteen-minute bars, leaving at a marketable limit once a bar closes there. The market data read is read-only, and nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/candle_closes/candle_closes/stop_on_a_closing_basis.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import candle_closes
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part


class ClosingBasisStop:
    """A protective exit that fires on a bar's close rather than on a touch.

    Attributes:
        share: The equities.Equity whose position is protected.
        bar_minutes: The float length of one bar in minutes.
    """

    def __init__(self):
        """Looks the share up and sets the bar length.

        Raises:
            Nothing.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.bar_minutes = 15

    def run(self) -> None:
        """Prints the exit's object with the level it watches.

        Returns:
            None.

        Raises:
            Nothing.
        """
        last_price = self.share.last_price
        level = round(last_price * 0.95, 2)
        part = order_part.OrderPart(
            side="protect",
            trigger=candle_closes.CandleCloses(
                level=level,
                bar_minutes=self.bar_minutes,
            ),
            pricing=marketable_pricing.MarketablePricing(),
        )
        print(f"Last price {last_price}, closing stop at {level}:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    ClosingBasisStop().run()
