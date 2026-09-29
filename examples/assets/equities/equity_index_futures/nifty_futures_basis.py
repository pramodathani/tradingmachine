"""Print the premium of every live Nifty futures contract over the index.

The program builds the Nifty 50 index once, hands it to each live futures contract as its underlying, and prints each contract's premium in points, in per cent and as an annual cost of carry.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity_index_futures/nifty_futures_basis.py
"""

from tradingmachine.assets import equities


class NiftyFuturesBasis:
    """The premium of each live futures contract on one equity index.

    Attributes:
        index: The tradingmachine.assets.equities.EquityIndex the contracts are written on.
    """

    def __init__(self, symbol: str = "NIFTY"):
        """Looks the index up in UBI.

        Args:
            symbol: The str nse symbol of the index, such as `NIFTY`.

        Raises:
            tradingmachine.assets.exceptions.EquityIndexError: UBI has no nse index with that symbol.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol=symbol)

    def run(self) -> None:
        """Builds every live contract and prints its premium.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.EquityIndexFuturesError: A listed contract could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        print(f"{self.index.symbol} index: {self.index.last_price}")
        expiries = equities.EquityIndexFutures.expiries(
            exchange="nse",
            underlying_symbol=self.index.symbol,
        )
        for expiry_date in expiries:
            contract = equities.EquityIndexFutures(
                exchange="nse",
                underlying_symbol=self.index.symbol,
                expiry_date=expiry_date,
                underlying=self.index,
            )
            basis_percent = contract.basis_percent
            cost_of_carry = contract.cost_of_carry
            print(f"{expiry_date}: price {contract.last_price}")
            if basis_percent is not None:
                print(f"    premium {basis_percent:.2f}% over the index")
            if cost_of_carry is not None:
                print(f"    cost of carry {cost_of_carry:.2f}% a year")


if __name__ == "__main__":
    NiftyFuturesBasis().run()
