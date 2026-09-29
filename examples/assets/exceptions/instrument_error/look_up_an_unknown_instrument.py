"""Look up an instrument UBI does not know and handle the InstrumentError.

The program asks the general Instrument class for a share whose symbol is misspelt, catches InstrumentError, and prints the message together with the UBI failure it was raised from, which carries the HTTP status code and the body UBI answered with.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/instrument_error/look_up_an_unknown_instrument.py
"""

from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class UnknownInstrumentLookup:
    """A lookup of a share by a misspelt symbol.

    Attributes:
        exchange: The str exchange to look the share up on.
        segment: The str UBI segment to look the share up in.
        symbol: The str misspelt symbol, which UBI does not know.
    """

    def __init__(self):
        """Creates the lookup with the misspelt symbol.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.segment = "equities"
        self.symbol = "RELIANCEINDUSTRIES"

    def run(self) -> None:
        """Looks the symbol up and prints what UBI said about it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup for a reason other than an unknown instrument.
        """
        try:
            instrument = instruments.Instrument(
                exchange=self.exchange,
                segment=self.segment,
                symbol=self.symbol,
            )
        except exceptions.InstrumentError as error:
            print(f"InstrumentError: {error}")
            cause = error.__cause__
            if cause is not None:
                print(f"Raised from {type(cause).__name__}")
                print(f"HTTP status code: {cause.status_code}")
                print(f"UBI answered: {cause.detail}")
            return
        print(f"Unexpectedly found: {instrument!r}")


if __name__ == "__main__":
    UnknownInstrumentLookup().run()
