"""Build icebergs that rest a little below the market, with fixed and with varied piece sizes.

The program reads Vodafone Idea's last price and tick size and builds two orders for 2000 shares limited two ticks below the last price, one showing 200 at a time and one whose pieces vary by up to a quarter either way so other traders cannot spot a repeating size. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/iceberg_execution/iceberg_execution/hidden_size_below_the_market.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import iceberg_execution
from tradingmachine.orders.plan_parts import order_part


class HiddenSizeBelowTheMarket:
    """Two icebergs for Vodafone Idea, one regular and one randomised.

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
        """Prints both orders' objects.

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
        limit_price = round(last_price - 2 * tick_size, 2)
        executions = {
            "200 at a time": iceberg_execution.IcebergExecution(
                visible_quantity=200,
            ),
            "about 200 at a time, varied by up to 25%": iceberg_execution.IcebergExecution(
                visible_quantity=200,
                randomise_percent=25,
            ),
        }
        print(f"Last price of {self.share.symbol}: {last_price}")
        for description, execution in executions.items():
            part = order_part.OrderPart(
                instrument=self.share,
                transaction_type="buy",
                quantity=2000,
                product="cnc",
                pricing=fixed_pricing.FixedPricing(
                    price=limit_price,
                    order_type="LIMIT",
                ),
                execution=execution,
            )
            print(f"An iceberg showing {description}:")
            print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    HiddenSizeBelowTheMarket().run()
