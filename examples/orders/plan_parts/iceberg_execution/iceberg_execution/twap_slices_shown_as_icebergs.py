"""Build a large buy of Vodafone Idea sent as TWAP slices, each shown as an iceberg.

The program reads Vodafone Idea's last price and builds an order for 6000 shares, limited one percent above that price, sent as six TWAP slices over an hour with each slice of 1000 shown 250 at a time and varied by up to a tenth. This is a nested execution: the `TwapExecution` passed as `execution` splits the order into slices, and the `IcebergExecution` passed as `inner_execution` works each slice. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/iceberg_execution/iceberg_execution/twap_slices_shown_as_icebergs.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import iceberg_execution
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import twap_execution


class TwapOfIcebergs:
    """A buy of Vodafone Idea worked as TWAP slices, each slice an iceberg.

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
        limit_price = round(last_price * 1.01, 2)
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="buy",
            quantity=6000,
            product="cnc",
            pricing=fixed_pricing.FixedPricing(
                price=limit_price,
                order_type="LIMIT",
            ),
            execution=twap_execution.TwapExecution(
                slices=6,
                over_minutes=60,
            ),
            inner_execution=iceberg_execution.IcebergExecution(
                visible_quantity=250,
                randomise_percent=10,
            ),
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    TwapOfIcebergs().run()
