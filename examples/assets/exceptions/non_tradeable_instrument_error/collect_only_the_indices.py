"""Collect the indices out of a mixed list of symbols, catching InstrumentError.

The program builds a NonTradeableInstrument for every entry of a list mixing indices and shares, keeps the ones that are indices, and prints their last values. A share raises NonTradeableInstrumentError and a symbol UBI does not know raises the base InstrumentError, and one handler for the base class skips both.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/non_tradeable_instrument_error/collect_only_the_indices.py
"""

from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class IndexCollector:
    """A collector of the indices in a list of symbols.

    Attributes:
        entries: The list of (str segment, str symbol) tuples on the nse to look at.
        indices: The list of tradingmachine.assets.instruments.NonTradeableInstrument found.
    """

    def __init__(self):
        """Creates the collector with the entries to look at.

        Raises:
            Nothing.
        """
        self.entries = [
            ("equity_indices", "NIFTY"),
            ("equities", "IDEA"),
            ("equity_indices", "BANKNIFTY"),
            ("equity_indices", "NIFTYSMALLCAPXYZ"),
        ]
        self.indices = []

    def run(self) -> None:
        """Builds every entry as an index, skips the ones that are not and prints the rest.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        for segment, symbol in self.entries:
            try:
                index = instruments.NonTradeableInstrument(
                    exchange="nse",
                    segment=segment,
                    symbol=symbol,
                )
            except exceptions.InstrumentError as error:
                print(f"Skipped {symbol}: {type(error).__name__}")
                continue
            self.indices.append(index)
        for index in self.indices:
            print(f"{index.symbol}: {index.last_price}")


if __name__ == "__main__":
    IndexCollector().run()
