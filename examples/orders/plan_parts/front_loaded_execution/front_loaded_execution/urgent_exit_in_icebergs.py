"""Build an urgent exit from a Vodafone Idea position that trades most of it early without showing its size.

The program builds a protecting sell for 4000 shares that starts when the price falls through 95% of the last price, sent front-loaded at an urgency of 0.8 over twenty minutes with each slice shown as an iceberg of 300. This is a nested execution: `FrontLoadedExecution` is the outer one and `IcebergExecution` the inner one. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/front_loaded_execution/front_loaded_execution/urgent_exit_in_icebergs.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import front_loaded_execution
from tradingmachine.orders.plan_parts import iceberg_execution
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses


class UrgentIcebergExit:
    """A front-loaded exit of icebergs from a Vodafone Idea position.

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
        """Prints the exit's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        level = round(last_price * 0.95, 2)
        part = order_part.OrderPart(
            side="protect",
            quantity=4000,
            trigger=price_crosses.PriceCrosses(level=level, direction="at_or_below"),
            pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
            execution=front_loaded_execution.FrontLoadedExecution(
                slices=5,
                over_minutes=20,
                urgency=0.8,
            ),
            inner_execution=iceberg_execution.IcebergExecution(
                visible_quantity=300,
            ),
        )
        print(
            f"Last price of {self.share.symbol}: {last_price}; the exit starts below {level}"
        )
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    UrgentIcebergExit().run()
