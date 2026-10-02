"""Build an entry in a share that waits for the Nifty index, not the share, to rise through a level.

The program reads the Nifty index's last price, sets a level 0.5% above it, and builds a `price_crosses` condition that watches the index through its `instrument` setting, so the object carries the index's `instrument_id`. A share bought on that condition enters when the whole market breaks out. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/price_crosses/price_crosses/entry_when_the_index_rises.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import price_crosses


class IndexTriggeredEntry:
    """An entry that waits for the Nifty index to rise through a level.

    Attributes:
        index: The tradingmachine.assets.equities.EquityIndex for the Nifty on the NSE.
    """

    def __init__(self):
        """Looks up the index.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The index could not be found in UBI.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")

    def build_order(self, level: float) -> order_part.OrderPart:
        """Builds the entry that waits for the index to reach a level.

        Args:
            level: The float index level.

        Returns:
            The tradingmachine.orders.plan_parts.order_part.OrderPart.

        Raises:
            Nothing.
        """
        return order_part.OrderPart(
            trigger=price_crosses.PriceCrosses(
                level=level,
                direction="at_or_above",
                instrument=self.index,
            ),
        )

    def run(self) -> None:
        """Prints the index's last price, the level and the entry's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the index.
        """
        last_price = self.index.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.index!r}")
        level = round(last_price * 1.005, 2)
        print(f"Nifty last price: {last_price}, level: {level}")
        print(json.dumps(self.build_order(level).document(), indent=2))


if __name__ == "__main__":
    IndexTriggeredEntry().run()
