"""Recover from a mistyped equity index symbol by catching EquityIndexError.

The program tries the spellings a person might type for the NIFTY 50 index, whose nse symbol is NIFTY, one after another, catches EquityIndexError for each one UBI does not know, and prints the identity of the first equity index that UBI does know.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/equity_index_error/recover_from_a_mistyped_symbol.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions


class MistypedSymbolRecovery:
    """A search for the first spelling of a equity index symbol that UBI knows.

    Attributes:
        exchange: The str exchange the equity index is listed on.
        candidate_symbols: The list of str spellings to try, in order.
    """

    def __init__(self):
        """Creates the search with the spellings to try.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.candidate_symbols = [
            "NIFTY 50",
            "NIFTY",
        ]

    def find_first_known(self) -> equities.EquityIndex | None:
        """Builds a EquityIndex from each spelling in turn until UBI knows one.

        Returns:
            The first equities.EquityIndex UBI knows, or None when UBI knows none of the spellings.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup for a reason other than an unknown symbol.
        """
        for symbol in self.candidate_symbols:
            try:
                return equities.EquityIndex(exchange=self.exchange, symbol=symbol)
            except exceptions.EquityIndexError as error:
                print(f"EquityIndexError for {symbol!r}: {error}")
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
