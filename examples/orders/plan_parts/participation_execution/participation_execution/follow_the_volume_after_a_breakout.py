"""Build a buy of Vodafone Idea that follows the market's volume once the price breaks out, each slice shown as an iceberg.

The program reads Vodafone Idea's last price and builds an order for 5000 shares that waits for the price to rise through 2% above it and then takes 8% of the volume traded from that moment, at most sixty slices by UBI's default, with each slice shown 100 at a time. This is a nested execution: `ParticipationExecution` is the outer one and `IcebergExecution` the inner one; participation may only be the outer. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/participation_execution/participation_execution/follow_the_volume_after_a_breakout.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import iceberg_execution
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import participation_execution
from tradingmachine.orders.plan_parts import price_crosses


class BreakoutParticipation:
    """A breakout buy of Vodafone Idea that follows the volume in icebergs.

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
        """Prints the order's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        level = round(last_price * 1.02, 2)
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="buy",
            quantity=5000,
            product="mis",
            trigger=price_crosses.PriceCrosses(level=level, direction="at_or_above"),
            pricing=marketable_pricing.MarketablePricing(buffer_ticks=1),
            execution=participation_execution.ParticipationExecution(percent=8.0),
            inner_execution=iceberg_execution.IcebergExecution(
                visible_quantity=100,
            ),
        )
        print(f"Last price of {self.share.symbol}: {last_price}; buying above {level}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    BreakoutParticipation().run()
