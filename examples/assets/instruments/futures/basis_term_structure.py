"""Print the basis term structure of Nifty futures.

The program builds every live Nifty future with the index given as its underlying, so the index is looked up only once, and prints each future's basis in points and per cent and the annual cost of carry it implies.

Typical usage example:

  .venv/bin/python examples/assets/instruments/futures/basis_term_structure.py
"""

from tradingmachine.assets import equities


class BasisTermStructure:
    """The basis and cost of carry of every live future on one index.

    Attributes:
        underlying_symbol: The str symbol of the index.
        index: The tradingmachine.assets.equities.EquityIndex the futures are written on.
    """

    def __init__(self, underlying_symbol: str = "NIFTY"):
        """Looks the index up in UBI.

        Args:
            underlying_symbol: The str symbol of an NSE index with futures.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.underlying_symbol = underlying_symbol
        self.index = equities.EquityIndex(exchange="nse", symbol=underlying_symbol)

    def run(self) -> None:
        """Prints one line per live future, soonest first.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        expiries = equities.EquityIndexFutures.expiries(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        print(f"{self.underlying_symbol} at {self.index.last_price}")
        print(f"{'Expiry':<12} {'Days':>5} {'Basis':>9} {'Basis %':>9} {'Carry %':>9}")
        for expiry_date in expiries:
            future = equities.EquityIndexFutures(
                exchange="nse",
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
                underlying=self.index,
            )
            basis = future.basis
            basis_percent = future.basis_percent
            carry = future.cost_of_carry
            if basis is None or basis_percent is None:
                print(f"{expiry_date!s:<12} a last price is missing")
                continue
            carry_text = "-"
            if carry is not None:
                carry_text = f"{carry:.2f}"
            print(
                f"{expiry_date!s:<12} {future.days_to_expiry:>5} "
                f"{basis:>9.2f} {basis_percent:>9.3f} {carry_text:>9}"
            )


if __name__ == "__main__":
    BasisTermStructure().run()
