"""Print the order book of the overnight MIBOR future with the most time left this quarter.

The program builds the overnight MIBOR future expiring next month on the nse and prints its best prices, its depth on each side, its volume and its open interest. Thinly traded contracts often have an empty book, which the program reports rather than failing on.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income_index_futures/mibor_futures_order_book.py
"""

from tradingmachine.assets import fixed_income


class MiborFuturesOrderBook:
    """The order book of one fixed income index future.

    Attributes:
        contract: The tradingmachine.assets.fixed_income.FixedIncomeIndexFutures whose book to print.
    """

    def __init__(self, underlying_symbol: str = "ONMIBOR"):
        """Builds the contract with the second expiry listed, or the only one.

        Args:
            underlying_symbol: The str symbol of the index, such as `ONMIBOR`.

        Raises:
            ValueError: No futures are listed on the index.
            tradingmachine.assets.exceptions.FixedIncomeIndexFuturesError: UBI has no such contract.
        """
        expiries = fixed_income.FixedIncomeIndexFutures.expiries(
            exchange="nse",
            underlying_symbol=underlying_symbol,
        )
        if not expiries:
            raise ValueError(f"No futures are listed on {underlying_symbol}")
        expiry_date = expiries[0]
        if len(expiries) > 1:
            expiry_date = expiries[1]
        self.contract = fixed_income.FixedIncomeIndexFutures(
            exchange="nse",
            underlying_symbol=underlying_symbol,
            expiry_date=expiry_date,
        )

    def run(self) -> None:
        """Prints the book and the day's activity.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        contract = self.contract
        print(f"{contract.underlying_symbol} future expiring {contract.expiry_date}")
        print(f"Last price: {contract.last_price}")
        bids = contract.bids
        offers = contract.offers
        if not bids and not offers:
            print("The order book is empty.")
        for bid in bids:
            print(f"Bid {bid['price']} for {bid['quantity']}")
        for offer in offers:
            print(f"Offer {offer['price']} for {offer['quantity']}")
        print(f"Spread: {contract.bid_offer_spread}")
        print(f"Volume: {contract.total_traded_volume}")
        print(f"Open interest: {contract.open_interest}")


if __name__ == "__main__":
    MiborFuturesOrderBook().run()
