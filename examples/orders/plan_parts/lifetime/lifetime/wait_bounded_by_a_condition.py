"""Build a dip entry whose wait ends if the index breaks down or the afternoon comes.

The program watches the NIFTY index and gives a dip entry on NSE IDEA a lifetime ending `when` either the index falls to 2 percent below its last value or it is 14:00, whichever comes first. The lifetime applies only to the wait, so an entry already sent is left to work. The market data read is read-only, and nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/lifetime/lifetime/wait_bounded_by_a_condition.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import any_condition
from tradingmachine.orders.plan_parts import lifetime
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses
from tradingmachine.orders.plan_parts import time_at


class BoundedDipEntry:
    """A dip entry whose wait ends on an index breakdown or at a time.

    Attributes:
        share: The equities.Equity bought on the dip.
        index: The equities.EquityIndex watched for a breakdown.
    """

    def __init__(self):
        """Looks the share and the index up.

        Raises:
            Nothing.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")

    def run(self) -> None:
        """Prints the entry's object with the levels it uses.

        Returns:
            None.

        Raises:
            Nothing.
        """
        entry_level = round(self.share.last_price * 0.98, 2)
        breakdown_level = round(self.index.last_price * 0.98, 2)
        ending = lifetime.Lifetime(
            when=any_condition.AnyCondition(
                [
                    price_crosses.PriceCrosses(
                        level=breakdown_level,
                        direction="at_or_below",
                        instrument=self.index,
                    ),
                    time_at.TimeAt("14:00"),
                ]
            ),
            applies_to="waiting",
        )
        part = order_part.OrderPart(
            trigger=price_crosses.PriceCrosses(level=entry_level),
            lifetime=ending,
        )
        print(
            f"Entry at {entry_level}, given up if the index reaches {breakdown_level} or at 14:00:"
        )
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    BoundedDipEntry().run()
