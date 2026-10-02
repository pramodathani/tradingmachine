"""Choose a marketable buffer by how liquid the instrument is, and compare what each buffer allows in rupees.

A marketable limit is sent a few ticks past the other side of the book, so a buffer that is too small misses the fill in a thin market and one too large allows a bad fill. The program reads Vodafone Idea's tick size and prints, for a liquid, an ordinary and a thin market, the buffer chosen, its `MarketablePricing` object and how far in rupees past the touch it reaches. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/marketable_pricing/marketable_pricing/buffer_by_liquidity.py
"""

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import marketable_pricing


class BufferByLiquidity:
    """Marketable buffers for three kinds of market.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        buffers: The dict of a str kind of market to the int buffer in ticks chosen for it.
    """

    def __init__(self):
        """Looks up the share and sets the buffers.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.buffers = {
            "liquid": 1,
            "ordinary": 2,
            "thin": 6,
        }

    def run(self) -> None:
        """Prints each buffer's object and its reach in rupees.

        Returns:
            None.

        Raises:
            Nothing.
        """
        tick_size = 0.05
        if self.share.tick_size is not None:
            tick_size = float(self.share.tick_size)
        print(f"Tick size of {self.share.symbol}: {tick_size}")
        for market, buffer_ticks in self.buffers.items():
            pricing = marketable_pricing.MarketablePricing(buffer_ticks=buffer_ticks)
            reach = round(buffer_ticks * tick_size, 2)
            print(
                f"{market:9} {pricing.document()} reaches {reach} rupees past the touch"
            )


if __name__ == "__main__":
    BufferByLiquidity().run()
