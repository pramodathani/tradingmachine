"""Print a snapshot of a share's order book and the trading figures around it.

The program builds Infosys as a TradeableInstrument and prints the five visible levels on each side of its order book, the spread in rupees and in ticks, the mid price, today's volume weighted average price, the size and time of the last trade and the volume so far. Each figure is read from UBI when it is asked for, so the snapshot takes a moment and its parts may be a moment apart.

Typical usage example:

  .venv/bin/python examples/assets/instruments/tradeable_instrument/order_book_snapshot.py
"""

from tradingmachine.assets import instruments


class OrderBookSnapshot:
    """A printed snapshot of one tradeable instrument's order book.

    Attributes:
        share: The tradingmachine.assets.instruments.TradeableInstrument whose book is printed.
    """

    def __init__(self, symbol: str = "INFY"):
        """Looks the share up in UBI.

        Args:
            symbol: The str NSE symbol of the share.

        Raises:
            tradingmachine.assets.exceptions.TradeableInstrumentError: The symbol names an index.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = instruments.TradeableInstrument(
            exchange="nse",
            segment="equities",
            symbol=symbol,
        )

    def print_book(self) -> None:
        """Prints the bids and the offers side by side, best first.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        bids = self.share.bids
        offers = self.share.offers
        print(f"{'Bid qty':>10} {'Bid':>10} | {'Offer':<10} {'Offer qty':<10}")
        for level in range(5):
            bid_text = f"{'':>10} {'':>10}"
            if level < len(bids):
                bid = bids[level]
                bid_text = f"{bid['quantity']:>10} {bid['price']:>10.2f}"
            offer_text = ""
            if level < len(offers):
                offer = offers[level]
                offer_text = f"{offer['price']:<10.2f} {offer['quantity']:<10}"
            print(f"{bid_text} | {offer_text}")

    def print_figures(self) -> None:
        """Prints the spread, the mid price and the day's trading figures.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        spread = self.share.bid_offer_spread
        if spread is None:
            print("Spread: one side of the book is empty")
        else:
            ticks = round(spread / float(self.share.tick_size))
            print(f"Spread: {spread:.2f} rupees, {ticks} ticks")
        print("Best bid:", self.share.best_bid)
        print("Best offer:", self.share.best_offer)
        print("Mid price:", self.share.mid_price)
        print("Average price today:", self.share.volume_weighted_average_price)
        print("Last trade:", self.share.last_quantity, "at", self.share.last_trade_time)
        print("Volume today:", self.share.total_traded_volume)

    def run(self) -> None:
        """Prints the whole snapshot.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        print(self.share, "last", self.share.last_price)
        self.print_book()
        self.print_figures()


if __name__ == "__main__":
    OrderBookSnapshot().run()
