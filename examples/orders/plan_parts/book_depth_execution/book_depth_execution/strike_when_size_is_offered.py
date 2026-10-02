"""Build a buy of Vodafone Idea that shows nothing and strikes only when enough size is offered at an acceptable price.

The program reads Vodafone Idea's last price and builds an order for 20000 shares that waits until at least 5000 are offered at or below half a percent above that price, then takes the smaller of what is shown and what is left. It is the `liquidity_seeking` preset written out: the pricing is a fixed limit at the same price, so a strike that only partly fills rests there. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/book_depth_execution/book_depth_execution/strike_when_size_is_offered.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import book_depth_execution
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part


class StrikeOnDisplayedSize:
    """A liquidity-seeking buy of Vodafone Idea.

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
        limit_price = round(last_price * 1.005, 2)
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="buy",
            quantity=20000,
            product="cnc",
            pricing=fixed_pricing.FixedPricing(
                price=limit_price,
                order_type="LIMIT",
            ),
            execution=book_depth_execution.BookDepthExecution(
                limit_price=limit_price,
                minimum_quantity=5000,
            ),
        )
        print(
            f"Last price of {self.share.symbol}: {last_price}; striking at {limit_price} or better"
        )
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    StrikeOnDisplayedSize().run()
