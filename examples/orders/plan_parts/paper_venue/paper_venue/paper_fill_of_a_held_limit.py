"""Build a paper version of a held limit buy of Vodafone Idea, which UBI fills from its queue estimate without sending anything to a broker.

A paper order waits on a `limit_marketable` trigger alone and takes no pricing of its own, because UBI holds it at the plan body's own limit price and fills it as a resting order at that price would have filled. The plan is that single order, since a paper order cannot be joined to orders that trade for real. The program reads the share's last price to suggest the limit price the plan's body should carry, and prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/paper_venue/paper_venue/paper_fill_of_a_held_limit.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import limit_marketable
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import paper_venue


class PaperHeldLimit:
    """A limit buy filled on paper.

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
        """Prints the suggested body price and the plan.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        plan = order_part.OrderPart(
            trigger=limit_marketable.LimitMarketable(),
            venue=paper_venue.PaperVenue(),
        )
        print(
            f"Body: a LIMIT buy of {self.share.symbol} at {round(last_price * 0.99, 2)}"
        )
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    PaperHeldLimit().run()
