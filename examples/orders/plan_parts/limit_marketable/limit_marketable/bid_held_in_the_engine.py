"""Build a limit buy held in UBI's engine until the offer comes down to it.

The program reads NSE IDEA's last price, which the plan's template would carry as its `LIMIT` price, and holds the order with a `limit_marketable` trigger, so nothing rests at the exchange until it would fill at once. The order takes no pricing of its own, because UBI holds it at the template's limit price. The market data read is read-only, and nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/limit_marketable/limit_marketable/bid_held_in_the_engine.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import limit_marketable
from tradingmachine.orders.plan_parts import order_part


class HeldBid:
    """A limit buy at the last price, held until the offer reaches it.

    Attributes:
        share: The equities.Equity bought.
    """

    def __init__(self):
        """Looks the share up.

        Raises:
            Nothing.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def run(self) -> None:
        """Prints the template's terms and the order's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        limit_price = self.share.last_price
        part = order_part.OrderPart(
            trigger=limit_marketable.LimitMarketable(),
        )
        print(f"Template: a LIMIT buy at {limit_price}, held in the engine:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    HeldBid().run()
