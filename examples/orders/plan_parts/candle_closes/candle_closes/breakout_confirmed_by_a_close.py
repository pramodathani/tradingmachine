"""Build a breakout entry that buys only after a five-minute bar closes above resistance.

A price that pokes through a level and falls straight back is not a breakout. The program reads the day's high of NSE IDEA and waits for a five-minute bar, UBI's default length, to close at or above it before buying at a marketable limit. The market data read is read-only, and nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/candle_closes/candle_closes/breakout_confirmed_by_a_close.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import candle_closes
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part


class ConfirmedBreakout:
    """A buy above the day's high, confirmed by a bar's close.

    Attributes:
        share: The equities.Equity bought on the breakout.
    """

    def __init__(self):
        """Looks the share up.

        Raises:
            Nothing.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def run(self) -> None:
        """Prints the entry's object with the level it watches.

        Returns:
            None.

        Raises:
            Nothing.
        """
        day_high = self.share.ohlc["high"]
        part = order_part.OrderPart(
            trigger=candle_closes.CandleCloses(
                level=day_high,
                direction="at_or_above",
            ),
            pricing=marketable_pricing.MarketablePricing(buffer_ticks=1),
        )
        print(f"The entry waits for a five-minute close at or above {day_high}:")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    ConfirmedBreakout().run()
