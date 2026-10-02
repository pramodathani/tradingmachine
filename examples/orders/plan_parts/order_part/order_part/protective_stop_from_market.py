"""Build an order that protects a long position with a stop resting at the broker, priced from the market.

The program reads Vodafone Idea's last price, sets a stop 3% below it with its limit one tick lower, and builds an order whose side is `protect`, so it sells against the long position the template's buy opened. It prints the order object UBI would read. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/order_part/order_part/protective_stop_from_market.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import native_stop_pricing
from tradingmachine.orders.plan_parts import order_part


class ProtectiveStop:
    """A protecting order with a native stop 3% below the market.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
    """

    def __init__(self):
        """Looks up the share.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def stop_prices(self) -> tuple[float, float]:
        """Works out the stop's trigger 3% below the last price, and its limit one tick below that.

        Returns:
            A tuple (trigger_price, limit_price) of floats in rupees, rounded to the tick size.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        tick_size = 0.05
        if self.share.tick_size is not None:
            tick_size = float(self.share.tick_size)
        trigger_ticks = round(last_price * 0.97 / tick_size)
        trigger_price = round(trigger_ticks * tick_size, 2)
        limit_price = round((trigger_ticks - 1) * tick_size, 2)
        return trigger_price, limit_price

    def run(self) -> None:
        """Prints the last price and the protecting order's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        trigger_price, limit_price = self.stop_prices()
        part = order_part.OrderPart(
            side="protect",
            pricing=native_stop_pricing.NativeStopPricing(
                trigger_price=trigger_price,
                limit_price=limit_price,
            ),
        )
        print(f"Last price of {self.share.symbol}: {self.share.last_price}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    ProtectiveStop().run()
