"""Build a buy stop above the market that protects a short position, resting at the broker.

For a short position the danger is a rise, so the protecting stop is a buy above the market. The program reads Vodafone Idea's last price, sets the stop's trigger 3% above it and its limit one tick higher, and builds a protecting order with that stop; with a template that sells, `protect` sends a buy. Because the stop rests at the broker it still fires if UBI's order engine is down. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/native_stop_pricing/native_stop_pricing/buy_stop_over_a_short_position.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import native_stop_pricing
from tradingmachine.orders.plan_parts import order_part


class ShortCoverStop:
    """A buy stop 3% above the market for a short position.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
    """

    def __init__(self):
        """Looks up the share.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def run(self) -> None:
        """Prints the stop's prices and the protecting order's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        tick_size = 0.05
        if self.share.tick_size is not None:
            tick_size = float(self.share.tick_size)
        trigger_ticks = round(last_price * 1.03 / tick_size)
        trigger_price = round(trigger_ticks * tick_size, 2)
        limit_price = round((trigger_ticks + 1) * tick_size, 2)
        part = order_part.OrderPart(
            side="protect",
            pricing=native_stop_pricing.NativeStopPricing(
                trigger_price=trigger_price,
                limit_price=limit_price,
            ),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(f"Buy stop triggered at {trigger_price}, limit {limit_price}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    ShortCoverStop().run()
