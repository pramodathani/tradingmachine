"""Place a limit bid that UBI's order engine holds, then cancel it.

The program bids for one Vodafone Idea share three per cent below the last price. UBI's order engine holds a plain day limit order until the offer comes down to its price, so the answer carries a parent id rather than a broker order id. The program reads the held order back and cancels it at once, whatever happens in between.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity/held_limit_order_round_trip.py
"""

from tradingmachine.assets import equities


class HeldLimitOrderRoundTrip:
    """One limit bid for a share, held by the order engine and then cancelled.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the bid is for.
        discount: The float fraction below the last price at which to bid, such as 0.03.
    """

    def __init__(self, symbol: str = "IDEA", discount: float = 0.03):
        """Looks the share up in UBI and stores how far below the market to bid.

        Args:
            symbol: The str nse symbol of the share, such as `IDEA`.
            discount: The float fraction below the last price at which to bid.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI has no nse share with that symbol.
        """
        self.share = equities.Equity(exchange="nse", symbol=symbol)
        self.discount = discount

    def bid_price(self) -> float:
        """Works out the bid price, rounded down to the share's tick size.

        Returns:
            The float price in rupees.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.ServiceUnavailableError: UBI has no quote for the share.
        """
        tick_size = float(self.share.tick_size)
        target = self.share.last_price * (1 - self.discount)
        ticks = int(target / tick_size)
        return round(ticks * tick_size, 2)

    def run(self) -> None:
        """Places the bid, prints what the engine holds, and cancels it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        price = self.bid_price()
        print(f"Last price {self.share.last_price}, bidding {price}")
        answer = self.share.buy_at_limit_price(
            price=price,
            quantity=1,
            product="mis",
            tag="exampleheldbid",
        )
        parent_id = answer.get("parent_id")
        try:
            print(f"Outcome: {answer['outcome']}, parent id: {parent_id}")
            if parent_id is not None:
                parent = self.share.parent(parent_id)
                print(f"The engine holds it in state {parent['state']}")
        finally:
            if parent_id is not None:
                cancelled = self.share.cancel_parent(parent_id)
                print(f"After cancelling: {cancelled['state']}")


if __name__ == "__main__":
    HeldLimitOrderRoundTrip().run()
