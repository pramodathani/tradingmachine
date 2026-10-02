"""Build a stop and a target that share one position, each shrinking as the other fills.

The program reads Vodafone Idea's last price and builds an either join with the sibling rule `reduce`: a native stop 3% below the market and a limit target 3% above it, both protecting the same position. If the target fills half the position, the stop is cut to the half that remains. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/either_part/either_part/stop_and_target_on_one_position.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import either_part
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import native_stop_pricing
from tradingmachine.orders.plan_parts import order_part


class StopAndTarget:
    """A stop and a target sharing one position of Vodafone Idea.

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

    def build_join(self, last_price: float) -> either_part.EitherPart:
        """Builds the stop and the target as one either join.

        Args:
            last_price: The float last price in rupees the levels are worked out from.

        Returns:
            The tradingmachine.orders.plan_parts.either_part.EitherPart.

        Raises:
            Nothing.
        """
        stop_price = self.price_from_market(last_price, -3)
        return either_part.EitherPart(
            children=[
                order_part.OrderPart(
                    side="protect",
                    pricing=native_stop_pricing.NativeStopPricing(
                        trigger_price=stop_price,
                        limit_price=round(stop_price - self.tick_size, 2),
                    ),
                ),
                order_part.OrderPart(
                    side="protect",
                    pricing=fixed_pricing.FixedPricing(
                        price=self.price_from_market(last_price, 3),
                        order_type="LIMIT",
                    ),
                ),
            ],
            sibling_rule="reduce",
        )

    def run(self) -> None:
        """Prints the last price and the join's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(self.build_join(last_price).document(), indent=2))


if __name__ == "__main__":
    StopAndTarget().run()
