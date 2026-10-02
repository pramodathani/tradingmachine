"""Build a protective stop for a Vodafone Idea holding that is sent again every trading morning for a week.

A native stop dies at the close, so a position held for days needs a new one each morning. The program reads Vodafone Idea's last price and builds a protecting stop 5% below it, sent by `DailyExecution` at UBI's default time of 09:20 and ended after five days by a lifetime in `after_days`. Once the stop trades no more is sent. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/daily_execution/daily_execution/stop_renewed_each_morning.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import daily_execution
from tradingmachine.orders.plan_parts import lifetime
from tradingmachine.orders.plan_parts import native_stop_pricing
from tradingmachine.orders.plan_parts import order_part


class DailyRenewedStop:
    """A stop for a Vodafone Idea holding renewed every morning for five days.

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
        """Prints the stop's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        tick_size = 0.01
        if self.share.tick_size is not None:
            tick_size = float(self.share.tick_size)
        trigger_price = round(last_price * 0.95, 2)
        limit_price = round(trigger_price - 5 * tick_size, 2)
        part = order_part.OrderPart(
            side="protect",
            product="cnc",
            pricing=native_stop_pricing.NativeStopPricing(
                trigger_price=trigger_price,
                limit_price=limit_price,
            ),
            execution=daily_execution.DailyExecution(),
            lifetime=lifetime.Lifetime(after_days=5),
        )
        print(
            f"Last price of {self.share.symbol}: {last_price}; stop at {trigger_price}"
        )
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    DailyRenewedStop().run()
