"""Combine two existing synthetic order types: a bracket whose entry waits for the price to touch a level.

The program reads Vodafone Idea's last price and names two presets in one order, `market_if_touched` 1% below the market and `bracket` with a stop 4% below and a target 3% above. UBI builds a then join out of the bracket around the touch-triggered entry, which no single fixed type offers. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/preset/preset/bracket_entered_on_a_touch.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import preset


class TouchBracket:
    """A bracket around an entry that waits for a touch.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        tick_size: The float tick size of the share in rupees.
    """

    def __init__(self):
        """Looks up the share and its tick size.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.tick_size = 0.05
        if self.share.tick_size is not None:
            self.tick_size = float(self.share.tick_size)

    def price_from_market(self, last_price: float, percent: float) -> float:
        """Gives a price a percentage away from the last price, rounded to the tick size.

        Args:
            last_price: The float last price in rupees.
            percent: The float percentage to move, negative for a price below the market.

        Returns:
            The float price in rupees.

        Raises:
            Nothing.
        """
        ticks = round(last_price * (1 + percent / 100) / self.tick_size)
        return round(ticks * self.tick_size, 2)

    def build_order(self, last_price: float) -> order_part.OrderPart:
        """Builds the order from the two presets.

        Args:
            last_price: The float last price in rupees the levels are worked out from.

        Returns:
            The tradingmachine.orders.plan_parts.order_part.OrderPart.

        Raises:
            Nothing.
        """
        stop_price = self.price_from_market(last_price, -4)
        return order_part.OrderPart(
            presets=[
                preset.Preset(
                    "market_if_touched",
                    trigger_price=self.price_from_market(last_price, -1),
                ),
                preset.Preset(
                    "bracket",
                    stop_price=stop_price,
                    stop_limit_price=round(stop_price - self.tick_size, 2),
                    target_price=self.price_from_market(last_price, 3),
                ),
            ],
        )

    def run(self) -> None:
        """Prints the last price and the order's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(self.build_order(last_price).document(), indent=2))


if __name__ == "__main__":
    TouchBracket().run()
