"""Call a futures discovery method on a base class, catch InstrumentError and use a family class instead.

The discovery class methods `expiries`, `contracts` and the like read the segment a family class such as EquityIndexFutures names. Called on the Futures base class, which names none, `expiries` raises FuturesError. The program catches it through its base class InstrumentError and asks EquityIndexFutures instead.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/futures_error/list_expiries_through_a_family_class.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class FuturesExpiryListing:
    """A listing of the NIFTY futures expiries.

    Attributes:
        exchange: The str exchange the futures trade on.
        underlying_symbol: The str symbol of the index.
    """

    def __init__(self):
        """Creates the listing for NIFTY futures.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.underlying_symbol = "NIFTY"

    def run(self) -> None:
        """Lists the expiries through the base class, recovers from the error and prints them.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        try:
            expiry_dates = instruments.Futures.expiries(
                exchange=self.exchange,
                underlying_symbol=self.underlying_symbol,
            )
        except exceptions.InstrumentError as error:
            print(f"{type(error).__name__}: {error}")
            expiry_dates = equities.EquityIndexFutures.expiries(
                exchange=self.exchange,
                underlying_symbol=self.underlying_symbol,
            )
        print(f"{self.underlying_symbol} futures expire on:")
        for expiry_date in expiry_dates:
            print(f"  {expiry_date}")


if __name__ == "__main__":
    FuturesExpiryListing().run()
