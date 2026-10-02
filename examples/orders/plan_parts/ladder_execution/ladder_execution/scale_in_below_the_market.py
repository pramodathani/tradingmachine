"""Build a buy of Vodafone Idea spread over five limit orders from just below the market down to 4% below it.

The program reads Vodafone Idea's last price and builds a ladder of five rungs from 1% to 4% below it for 10000 shares, so 2000 rest at each rung. Every rung is sent at once and rounded to the tick on the passive side, and the rung prices replace any pricing, so the order has none. The program prints the document and the rung prices before rounding. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/ladder_execution/ladder_execution/scale_in_below_the_market.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import ladder_execution
from tradingmachine.orders.plan_parts import order_part


class LadderedEntry:
    """A five-rung buy ladder for Vodafone Idea.

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
        """Prints the order's object and the rung prices.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        execution = ladder_execution.LadderExecution(
            from_price=round(last_price * 0.99, 2),
            to_price=round(last_price * 0.96, 2),
            steps=5,
        )
        part = order_part.OrderPart(
            instrument=self.share,
            transaction_type="buy",
            quantity=10000,
            product="cnc",
            execution=execution,
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(part.document(), indent=2))
        gap = (execution.to_price - execution.from_price) / (execution.steps - 1)
        for rung in range(execution.steps):
            print(f"Rung {rung + 1}: about {execution.from_price + rung * gap:.4f}")


if __name__ == "__main__":
    LadderedEntry().run()
