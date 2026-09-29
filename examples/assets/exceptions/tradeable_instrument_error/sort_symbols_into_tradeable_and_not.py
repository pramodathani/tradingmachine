"""Sort a list of symbols into ones that can be traded and ones that cannot, catching InstrumentError.

The program builds a TradeableInstrument for every entry of a list mixing shares and indices. An index raises TradeableInstrumentError, and a symbol UBI does not know raises the base InstrumentError, so one handler for the base class catches both and the error's class says which list the entry belongs in.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/tradeable_instrument_error/sort_symbols_into_tradeable_and_not.py
"""

from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class TradeableSorter:
    """A sorter of symbols by whether UBI lets them be traded.

    Attributes:
        entries: The list of (str segment, str symbol) tuples on the nse to sort.
        tradeable: The list of str symbols that can be traded.
        not_tradeable: The list of str symbols that are indices.
        unknown: The list of str symbols UBI does not know.
    """

    def __init__(self):
        """Creates the sorter with the entries to sort.

        Raises:
            Nothing.
        """
        self.entries = [
            ("equities", "IDEA"),
            ("equity_indices", "NIFTY"),
            ("equities", "RELIANCE"),
            ("equity_indices", "BANKNIFTY"),
            ("equities", "NOTASHARE"),
        ]
        self.tradeable = []
        self.not_tradeable = []
        self.unknown = []

    def sort_entry(self, segment: str, symbol: str) -> None:
        """Builds one entry as tradeable and records which list it belongs in.

        Args:
            segment: The str UBI segment of the entry.
            symbol: The str symbol of the entry.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        try:
            instruments.TradeableInstrument(
                exchange="nse",
                segment=segment,
                symbol=symbol,
            )
        except exceptions.InstrumentError as error:
            if isinstance(error, exceptions.TradeableInstrumentError):
                self.not_tradeable.append(symbol)
            else:
                self.unknown.append(symbol)
            return
        self.tradeable.append(symbol)

    def run(self) -> None:
        """Sorts every entry and prints the three lists.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup.
        """
        for segment, symbol in self.entries:
            self.sort_entry(segment, symbol)
        print(f"Tradeable: {self.tradeable}")
        print(f"Indices, which cannot be traded: {self.not_tradeable}")
        print(f"Unknown to UBI: {self.unknown}")


if __name__ == "__main__":
    TradeableSorter().run()
