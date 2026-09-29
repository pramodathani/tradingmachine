"""Find the most traded dollar-rupee future on the nse and report on it.

USDINR futures on the nse expire every week as well as every month, and most of the trading is in one or two of them. The program builds the first six contracts, picks the one with the highest volume today, and prints its prices and order book. It also prints the contract's `lot_size`, which here is the plurality of the brokers' figures rather than the lot an order is measured against, so it must not be used to size an order.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency_futures/usdinr_futures_report.py
"""

from tradingmachine.assets import currencies


class DollarRupeeFuturesReport:
    """A report on the most traded futures contract on one currency pair.

    Attributes:
        underlying_symbol: The str symbol of the pair, such as `USDINR`.
        contracts_to_compare: The int number of soonest contracts to compare.
    """

    def __init__(
        self, underlying_symbol: str = "USDINR", contracts_to_compare: int = 6
    ):
        """Stores the pair and how many contracts to compare.

        Args:
            underlying_symbol: The str symbol of the pair.
            contracts_to_compare: The int number of soonest contracts to compare.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol
        self.contracts_to_compare = contracts_to_compare

    def most_traded(self) -> currencies.CurrencyFutures | None:
        """Builds the soonest contracts and keeps the one with the highest volume.

        Returns:
            The tradingmachine.assets.currencies.CurrencyFutures traded most today, or None when none is listed.

        Raises:
            tradingmachine.assets.exceptions.CurrencyFuturesError: A listed contract could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiries = currencies.CurrencyFutures.expiries(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        best_contract = None
        best_volume = -1
        for expiry_date in expiries[: self.contracts_to_compare]:
            contract = currencies.CurrencyFutures(
                exchange="nse",
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
            )
            volume = contract.total_traded_volume
            if volume is None:
                volume = 0
            print(f"{expiry_date}: volume {volume}")
            if volume > best_volume:
                best_volume = volume
                best_contract = contract
        return best_contract

    def run(self) -> None:
        """Chooses the contract and prints the report.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        contract = self.most_traded()
        if contract is None:
            print(f"No futures are listed on {self.underlying_symbol}.")
            return
        print(f"Most traded: {contract.underlying_symbol} {contract.expiry_date}")
        print(f"Kind of expiry: {contract.expiry_kind}")
        print(f"Last price: {contract.last_price}")
        print(f"Tick size: {contract.tick_size}")
        print(f"Best bid: {contract.best_bid}")
        print(f"Best offer: {contract.best_offer}")
        print(f"Spread: {contract.bid_offer_spread}")
        print(f"Open interest: {contract.open_interest}")
        print(f"lot_size says {contract.lot_size}, which is not the order lot")


if __name__ == "__main__":
    DollarRupeeFuturesReport().run()
