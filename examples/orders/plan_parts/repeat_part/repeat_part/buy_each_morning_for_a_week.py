"""Build a weekly buying programme: a delivery buy of Vodafone Idea at twenty past nine on each of the next five trading days.

With `every_trading_day_at`, UBI sends each copy at that time on its own trading day, skipping weekends and holidays, and keeps the plan across days; the first copy goes today if the time has not passed and the day trades. Each copy is a limit order 1% below the last price read now, so a copy that does not fill is left resting until the day ends. It prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/repeat_part/repeat_part/buy_each_morning_for_a_week.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import repeat_part


class MorningBuys:
    """Five delivery buys, one each trading morning.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        trading_days: The int number of mornings.
        send_time: The str time of day each buy is sent.
    """

    def __init__(self):
        """Looks the share up and sets the schedule.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.trading_days = 5
        self.send_time = "09:20"

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
        limit_price = round(last_price * 0.99, 2)
        plan = repeat_part.RepeatPart(
            child=order_part.OrderPart(
                quantity=200,
                product="cnc",
                pricing=fixed_pricing.FixedPricing(
                    price=limit_price,
                    order_type="LIMIT",
                ),
            ),
            times=self.trading_days,
            every_trading_day_at=self.send_time,
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    MorningBuys().run()
