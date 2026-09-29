"""Recover from a mistyped currency index symbol by catching CurrencyIndexError.

The program tries the spellings a person might type for a dollar index, which UBI does not carry at all, one after another, catches CurrencyIndexError for each one UBI does not know, and prints the identity of the first currency index that UBI does know.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/currency_index_error/recover_from_a_mistyped_symbol.py
"""

from tradingmachine.assets import currencies
from tradingmachine.assets import exceptions


class MistypedSymbolRecovery:
    """A search for the first spelling of a currency index symbol that UBI knows.

    Attributes:
        exchange: The str exchange the currency index is listed on.
        candidate_symbols: The list of str spellings to try, in order.
    """

    def __init__(self):
        """Creates the search with the spellings to try.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.candidate_symbols = [
            "DOLLARINDEX",
            "USDX",
        ]

    def find_first_known(self) -> currencies.CurrencyIndex | None:
        """Builds a CurrencyIndex from each spelling in turn until UBI knows one.

        Returns:
            The first currencies.CurrencyIndex UBI knows, or None when UBI knows none of the spellings.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup for a reason other than an unknown symbol.
        """
        for symbol in self.candidate_symbols:
            try:
                return currencies.CurrencyIndex(exchange=self.exchange, symbol=symbol)
            except exceptions.CurrencyIndexError as error:
                print(f"CurrencyIndexError for {symbol!r}: {error}")
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
                f"UBI knows none of {self.candidate_symbols} on the {self.exchange}, which is expected for a segment that holds no rows on any exchange."
            )
            return
        print(f"Found: {found!r}")
        print(f"Instrument id: {found.instrument_id}")
        print(f"Tick size: {found.tick_size}")
        print(f"Lot size: {found.lot_size}")


if __name__ == "__main__":
    MistypedSymbolRecovery().run()
