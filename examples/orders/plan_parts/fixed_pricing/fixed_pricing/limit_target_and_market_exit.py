"""Build a limit target and a market exit for one position, the two common uses of fixed pricing.

The program reads Vodafone Idea's last price and builds two protecting orders, one priced as a limit 2% above the market for taking profit, and one priced at market for getting out at once. UBI writes the order type in capitals here, `LIMIT` and `MARKET`. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/fixed_pricing/fixed_pricing/limit_target_and_market_exit.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import order_part


class TargetAndMarketExit:
    """A limit target and a market exit for a position in Vodafone Idea.

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
        """Prints the target price and both orders' objects.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        target_price = round(last_price * 1.02, 2)
        target = order_part.OrderPart(
            side="protect",
            pricing=fixed_pricing.FixedPricing(price=target_price, order_type="LIMIT"),
        )
        market_exit = order_part.OrderPart(
            side="protect",
            pricing=fixed_pricing.FixedPricing(order_type="MARKET"),
        )
        print(
            f"Last price of {self.share.symbol}: {last_price}, target: {target_price}"
        )
        print(json.dumps(target.document(), indent=2))
        print(json.dumps(market_exit.document(), indent=2))


if __name__ == "__main__":
    TargetAndMarketExit().run()
