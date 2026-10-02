"""Build an accumulation: a buy of Vodafone Idea every half hour, six times, stopped if the price runs 3% higher.

The program reads the share's last price and repeats one marketable buy of 500 shares every 30 minutes, the first at once. The `until` condition ends every copy still waiting once the price rises 3% above today's level, while copies already sent are left as they are. It prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/repeat_part/repeat_part/accumulate_every_half_hour.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses
from tradingmachine.orders.plan_parts import repeat_part


class HalfHourlyAccumulation:
    """Six buys half an hour apart, ended early by a rally.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        purchases: The int number of buys.
        minutes_apart: The float minutes between buys.
    """

    def __init__(self):
        """Looks the share up and sets the schedule.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.purchases = 6
        self.minutes_apart = 30.0

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
        stop_buying_level = round(last_price * 1.03, 2)
        plan = repeat_part.RepeatPart(
            child=order_part.OrderPart(
                quantity=500,
                pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
            ),
            times=self.purchases,
            every_minutes=self.minutes_apart,
            until=price_crosses.PriceCrosses(
                level=stop_buying_level,
                direction="at_or_above",
            ),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    HalfHourlyAccumulation().run()
