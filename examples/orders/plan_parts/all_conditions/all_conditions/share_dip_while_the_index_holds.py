"""Build an entry that buys a dip in a share only while the Nifty index is still above a floor, and only after ten.

A share falling on its own may be a bargain, while a share falling with the whole market usually is not. The program reads Vodafone Idea's and the Nifty index's last prices and joins three conditions in an `AllConditions` group: the time is after 10:00, the share has dipped 1%, and the index is no more than 0.5% below its last price. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/all_conditions/all_conditions/share_dip_while_the_index_holds.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import all_conditions
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses
from tradingmachine.orders.plan_parts import time_after


class DipWhileIndexHolds:
    """An entry on a share's dip, guarded by the time and the index.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        index: The tradingmachine.assets.equities.EquityIndex for the Nifty on the NSE.
    """

    def __init__(self):
        """Looks up the share and the index.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share or the index could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")

    def last_price(self, instrument: equities.Equity | equities.EquityIndex) -> float:
        """Reads an instrument's last price.

        Args:
            instrument: The tradingmachine.assets.equities.Equity or tradingmachine.assets.equities.EquityIndex to read.

        Returns:
            The float last price.

        Raises:
            ValueError: UBI has no last price for the instrument.
        """
        last_price = instrument.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {instrument!r}")
        return last_price

    def run(self) -> None:
        """Prints the levels and the entry's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share or the index.
        """
        dip_level = round(self.last_price(self.share) * 0.99, 2)
        index_floor = round(self.last_price(self.index) * 0.995, 2)
        part = order_part.OrderPart(
            trigger=all_conditions.AllConditions(
                [
                    time_after.TimeAfter("10:00"),
                    price_crosses.PriceCrosses(
                        level=dip_level,
                        direction="at_or_below",
                    ),
                    price_crosses.PriceCrosses(
                        level=index_floor,
                        direction="at_or_above",
                        instrument=self.index,
                    ),
                ]
            ),
        )
        print(f"Share dip level: {dip_level}, index floor: {index_floor}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    DipWhileIndexHolds().run()
