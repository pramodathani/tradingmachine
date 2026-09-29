"""Recover from a mistyped bond symbol by catching FixedIncomeError.

The program tries the spellings a person might type for a government bond, whose ISIN is IN000126C010, one after another, catches FixedIncomeError for each one UBI does not know, and prints the identity of the first bond that UBI does know.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/fixed_income_error/recover_from_a_mistyped_symbol.py
"""

from tradingmachine.assets import fixed_income
from tradingmachine.assets import exceptions


class MistypedSymbolRecovery:
    """A search for the first spelling of a bond symbol that UBI knows.

    Attributes:
        exchange: The str exchange the bond is listed on.
        candidate_symbols: The list of str spellings to try, in order.
    """

    def __init__(self):
        """Creates the search with the spellings to try.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.candidate_symbols = [
            "IN000126C01",
            "IN000126C010",
        ]

    def find_first_known(self) -> fixed_income.FixedIncome | None:
        """Builds a FixedIncome from each spelling in turn until UBI knows one.

        Returns:
            The first fixed_income.FixedIncome UBI knows, or None when UBI knows none of the spellings.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup for a reason other than an unknown symbol.
        """
        for symbol in self.candidate_symbols:
            try:
                return fixed_income.FixedIncome(exchange=self.exchange, symbol=symbol)
            except exceptions.FixedIncomeError as error:
                print(f"FixedIncomeError for {symbol!r}: {error}")
        return None

    def run(self) -> None:
        """Finds the first known spelling and prints the identity UBI gives it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup.
        """
        found = self.find_first_known()
        if found is None:
            print(
                f"UBI knows none of {self.candidate_symbols} on the {self.exchange}, which is expected for a mistyped name."
            )
            return
        print(f"Found: {found!r}")
        print(f"Instrument id: {found.instrument_id}")
        print(f"Tick size: {found.tick_size}")
        print(f"Lot size: {found.lot_size}")


if __name__ == "__main__":
    MistypedSymbolRecovery().run()
