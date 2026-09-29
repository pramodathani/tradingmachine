"""Recover from a mistyped fixed income index symbol by catching FixedIncomeIndexError.

The program tries the spellings a person might type for the ten-year government bond index, whose nse symbol is 10YGS7, one after another, catches FixedIncomeIndexError for each one UBI does not know, and prints the identity of the first fixed income index that UBI does know.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/fixed_income_index_error/recover_from_a_mistyped_symbol.py
"""

from tradingmachine.assets import fixed_income
from tradingmachine.assets import exceptions


class MistypedSymbolRecovery:
    """A search for the first spelling of a fixed income index symbol that UBI knows.

    Attributes:
        exchange: The str exchange the fixed income index is listed on.
        candidate_symbols: The list of str spellings to try, in order.
    """

    def __init__(self):
        """Creates the search with the spellings to try.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.candidate_symbols = [
            "10YGS",
            "10YGS7",
        ]

    def find_first_known(self) -> fixed_income.FixedIncomeIndex | None:
        """Builds a FixedIncomeIndex from each spelling in turn until UBI knows one.

        Returns:
            The first fixed_income.FixedIncomeIndex UBI knows, or None when UBI knows none of the spellings.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup for a reason other than an unknown symbol.
        """
        for symbol in self.candidate_symbols:
            try:
                return fixed_income.FixedIncomeIndex(
                    exchange=self.exchange, symbol=symbol
                )
            except exceptions.FixedIncomeIndexError as error:
                print(f"FixedIncomeIndexError for {symbol!r}: {error}")
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
