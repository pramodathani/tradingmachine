"""Work out the basis of futures in several families, catching InstrumentError where there is no underlying.

The basis is a future's price minus its underlying's price. It can be worked out for a NIFTY future, whose underlying is the NIFTY index, but not for a USDINR currency future or a government bond future, whose cash underlyings have no price in UBI. Those raise UnderlyingError, which the program catches through its base class InstrumentError.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/underlying_error/basis_of_futures_across_families.py
"""

from tradingmachine.assets import currencies
from tradingmachine.assets import equities
from tradingmachine.assets import exceptions
from tradingmachine.assets import fixed_income
from tradingmachine.assets import instruments


class BasisReport:
    """A report of the basis of the nearest future in three families.

    Attributes:
        contracts: The list of tradingmachine.assets.instruments.Futures to report on.
    """

    def __init__(self):
        """Creates the report with no contracts yet.

        Raises:
            Nothing.
        """
        self.contracts = []

    def collect_contracts(self) -> None:
        """Builds the nearest NIFTY, USDINR and 6.33% 2035 bond futures.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the contracts.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        nifty_expiry = equities.EquityIndexFutures.expiries("nse", "NIFTY")[0]
        self.contracts.append(
            equities.EquityIndexFutures(
                exchange="nse",
                underlying_symbol="NIFTY",
                expiry_date=nifty_expiry,
            )
        )
        dollar_expiry = currencies.CurrencyFutures.expiries("nse", "USDINR")[0]
        self.contracts.append(
            currencies.CurrencyFutures(
                exchange="nse",
                underlying_symbol="USDINR",
                expiry_date=dollar_expiry,
            )
        )
        bond_expiry = fixed_income.FixedIncomeFutures.expiries("nse", "633GS2035")[0]
        self.contracts.append(
            fixed_income.FixedIncomeFutures(
                exchange="nse",
                underlying_symbol="633GS2035",
                expiry_date=bond_expiry,
            )
        )

    def describe_basis(self, contract: instruments.Futures) -> str:
        """Works out one contract's basis and describes it.

        Args:
            contract: The tradingmachine.assets.instruments.Futures to describe.

        Returns:
            A str line with the basis, or with the reason there is none.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        label = f"{contract.underlying_symbol} {contract.expiry_date}"
        try:
            basis = contract.basis
        except exceptions.InstrumentError as error:
            return f"{label}: no basis, {type(error).__name__}"
        return f"{label}: basis {basis}"

    def run(self) -> None:
        """Builds the contracts and prints the basis of each.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the contracts.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        self.collect_contracts()
        for contract in self.contracts:
            print(self.describe_basis(contract))


if __name__ == "__main__":
    BasisReport().run()
