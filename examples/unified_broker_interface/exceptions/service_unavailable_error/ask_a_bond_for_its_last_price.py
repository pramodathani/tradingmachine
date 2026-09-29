"""Ask a government bond for its last price and handle the ServiceUnavailableError.

No broker that serves quotes carries a cash bond, so UBI answers a request for a bond's last price with HTTP 503. The program catches ServiceUnavailableError and falls back to the bond's details, which UBI does have, printing its lot size and tick size instead.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/service_unavailable_error/ask_a_bond_for_its_last_price.py
"""

from tradingmachine.assets import fixed_income
from tradingmachine.unified_broker_interface import exceptions


class BondQuoteReport:
    """A report on one government bond that copes with having no quote.

    Attributes:
        bond: The tradingmachine.assets.fixed_income.FixedIncome reported on.
    """

    def __init__(self):
        """Creates the report for the bond with ISIN IN000126C010.

        Raises:
            tradingmachine.assets.exceptions.FixedIncomeError: UBI does not know the bond.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.bond = fixed_income.FixedIncome(exchange="nse", symbol="IN000126C010")

    def run(self) -> None:
        """Asks for the last price and prints it, or the bond's details when there is none.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI failed for a reason other than a missing quote.
        """
        print(f"Bond: {self.bond!r}")
        try:
            last_price = self.bond.last_price
        except exceptions.ServiceUnavailableError as error:
            print(f"ServiceUnavailableError ({error.status_code}): {error.message}")
            print(f"Lot size: {self.bond.lot_size}")
            print(f"Tick size: {self.bond.tick_size}")
            return
        print(f"Last price: {last_price}")


if __name__ == "__main__":
    BondQuoteReport().run()
