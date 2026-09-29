"""Bid for one lot of a dollar-rupee future well below the market, then cancel the bid.

The program bids for one lot of the most traded of the six soonest USDINR futures, one per cent below its last price, which for a currency pair is far outside a day's move. The quantity is counted in dollars and must be a whole number of lots, so the program sends the exchange's lot of 1,000 dollars rather than the contract's `lot_size`, which for currencies is not the lot an order is measured against. UBI's order engine holds a plain day limit order until the offer comes down to its price, so the program cancels the parent at once.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency_futures/usdinr_held_limit_order.py
"""

from tradingmachine.assets import currencies


class DollarRupeeHeldLimitOrder:
    """One far-away bid for a currency future, held by the order engine and then cancelled.

    Attributes:
        LOT_IN_DOLLARS: The int number of dollars in one lot of an nse USDINR future, which is what an order's quantity is counted against.
        contract: The tradingmachine.assets.currencies.CurrencyFutures the bid is for.
        discount: The float fraction below the last price at which to bid.
    """

    LOT_IN_DOLLARS = 1000

    def __init__(self, discount: float = 0.01):
        """Builds the most traded of the soonest USDINR contracts.

        Args:
            discount: The float fraction below the last price at which to bid.

        Raises:
            ValueError: No USDINR futures are listed.
            tradingmachine.assets.exceptions.CurrencyFuturesError: UBI has no such contract.
        """
        expiries = currencies.CurrencyFutures.expiries(
            exchange="nse",
            underlying_symbol="USDINR",
        )
        if not expiries:
            raise ValueError("No USDINR futures are listed")
        best_contract = None
        best_volume = -1
        for expiry_date in expiries[:6]:
            contract = currencies.CurrencyFutures(
                exchange="nse",
                underlying_symbol="USDINR",
                expiry_date=expiry_date,
            )
            volume = contract.total_traded_volume
            if volume is None:
                volume = 0
            if volume > best_volume:
                best_volume = volume
                best_contract = contract
        self.contract = best_contract
        self.discount = discount

    def bid_price(self) -> float:
        """Works out the bid price, rounded down to the contract's tick size.

        Returns:
            The float rate in rupees per dollar.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.ServiceUnavailableError: UBI has no quote for the contract.
        """
        tick_size = float(self.contract.tick_size)
        target = self.contract.last_price * (1 - self.discount)
        ticks = int(target / tick_size)
        return round(ticks * tick_size, 4)

    def run(self) -> None:
        """Places the bid for one lot, prints the engine's answer and cancels it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        contract = self.contract
        price = self.bid_price()
        print(f"USDINR future expiring {contract.expiry_date}")
        print(f"Last price {contract.last_price}, bidding {price}")
        print(f"Quantity: one lot of {self.LOT_IN_DOLLARS} dollars")
        answer = contract.buy_at_limit_price(
            price=price,
            quantity=self.LOT_IN_DOLLARS,
            product="nrml",
            tag="exampleusdinrbid",
        )
        parent_id = answer.get("parent_id")
        try:
            print(f"Outcome: {answer['outcome']}, parent id: {parent_id}")
            if parent_id is not None:
                parent = contract.parent(parent_id)
                print(f"The engine holds it in state {parent['state']}")
        finally:
            if parent_id is not None:
                cancelled = contract.cancel_parent(parent_id)
                print(f"After cancelling: {cancelled['state']}")


if __name__ == "__main__":
    DollarRupeeHeldLimitOrder().run()
