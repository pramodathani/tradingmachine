"""List futures expiries on an exchange UBI does not know, catching UnifiedBrokerInterfaceError.

UBI knows the nse, bse, mcx and ncdex exchanges. The program asks for RELIANCE futures expiries on the nyse, catches the BadRequestError UBI answers with through its base class UnifiedBrokerInterfaceError, prints UBI's list of valid exchanges and asks again on the nse.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/bad_request_error/list_expiries_on_an_unknown_exchange.py
"""

import datetime

from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class ExpiryListing:
    """A listing of RELIANCE futures expiries that corrects a wrong exchange.

    Attributes:
        exchanges: The list of str exchanges to try, in order.
        underlying_symbol: The str symbol of the share.
    """

    def __init__(self):
        """Creates the listing with the exchanges to try.

        Raises:
            Nothing.
        """
        self.exchanges = [
            "nyse",
            "nse",
        ]
        self.underlying_symbol = "RELIANCE"

    def list_expiries(self) -> list[datetime.date]:
        """Tries each exchange in turn until UBI accepts one.

        Returns:
            The list of datetime.date expiries from the first exchange UBI accepts, or an empty list when it accepts none.

        Raises:
            Nothing.
        """
        for exchange in self.exchanges:
            try:
                return equities.EquityFutures.expiries(
                    exchange=exchange,
                    underlying_symbol=self.underlying_symbol,
                )
            except exceptions.UnifiedBrokerInterfaceError as error:
                print(
                    f"{exchange}: {type(error).__name__} ({error.status_code}): {error.message}"
                )
        return []

    def run(self) -> None:
        """Lists the expiries and prints them.

        Returns:
            None.

        Raises:
            Nothing.
        """
        expiry_dates = self.list_expiries()
        print(f"{self.underlying_symbol} futures expire on:")
        for expiry_date in expiry_dates:
            print(f"  {expiry_date}")


if __name__ == "__main__":
    ExpiryListing().run()
