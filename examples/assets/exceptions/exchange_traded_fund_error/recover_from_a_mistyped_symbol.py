"""Recover from a mistyped exchange traded fund symbol by catching ExchangeTradedFundError.

The program tries the spellings a person might type for the Nifty BeES fund, whose nse symbol is NIFTYBEES, one after another, catches ExchangeTradedFundError for each one UBI does not know, and prints the identity of the first exchange traded fund that UBI does know.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/exchange_traded_fund_error/recover_from_a_mistyped_symbol.py
"""

from tradingmachine.assets import funds
from tradingmachine.assets import exceptions


class MistypedSymbolRecovery:
    """A search for the first spelling of a exchange traded fund symbol that UBI knows.

    Attributes:
        exchange: The str exchange the exchange traded fund is listed on.
        candidate_symbols: The list of str spellings to try, in order.
    """

    def __init__(self):
        """Creates the search with the spellings to try.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.candidate_symbols = [
            "NIFTY BEES",
            "NIFTYBEES",
        ]

    def find_first_known(self) -> funds.ExchangeTradedFund | None:
        """Builds a ExchangeTradedFund from each spelling in turn until UBI knows one.

        Returns:
            The first funds.ExchangeTradedFund UBI knows, or None when UBI knows none of the spellings.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup for a reason other than an unknown symbol.
        """
        for symbol in self.candidate_symbols:
            try:
                return funds.ExchangeTradedFund(exchange=self.exchange, symbol=symbol)
            except exceptions.ExchangeTradedFundError as error:
                print(f"ExchangeTradedFundError for {symbol!r}: {error}")
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
