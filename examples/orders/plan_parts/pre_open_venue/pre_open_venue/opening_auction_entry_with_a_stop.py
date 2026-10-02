"""Build an entry into Vodafone Idea at the opening auction, protected by a stop once it fills.

The first plan of a then join is a market buy sent into the pre-open at UBI's default time of 09:00:30, which is before the 09:05 cut-off for market orders. Its fills are protected by a native stop 3% below the last price read now, placed once the auction has filled the entry and the market opens. It prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/pre_open_venue/pre_open_venue/opening_auction_entry_with_a_stop.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import native_stop_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import pre_open_venue
from tradingmachine.orders.plan_parts import then_part


class AuctionEntryWithStop:
    """A pre-open market buy followed by a protecting stop.

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
        stop_trigger = round(last_price * 0.97, 2)
        plan = then_part.ThenPart(
            first=order_part.OrderPart(
                pricing=fixed_pricing.FixedPricing(order_type="MARKET"),
                venue=pre_open_venue.PreOpenVenue(),
            ),
            each_fill=order_part.OrderPart(
                side="protect",
                pricing=native_stop_pricing.NativeStopPricing(
                    trigger_price=stop_trigger,
                    limit_price=round(stop_trigger - 0.05, 2),
                ),
            ),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    AuctionEntryWithStop().run()
