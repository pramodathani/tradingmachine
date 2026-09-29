"""Try to build a currency index future and handle the error UBI gives today.

UBI holds no rows in its currency index futures segment, so every lookup fails with CurrencyIndexFuturesError. The program asks for a future on a dollar index at the expiry of the soonest USDINR future, which is a date on which currency contracts do expire, catches the error, and prints it.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency_index_futures/lookup_error_handled.py
"""

from tradingmachine.assets import currencies
from tradingmachine.assets import exceptions


class CurrencyIndexFuturesLookup:
    """An attempt to build one currency index futures contract.

    Attributes:
        underlying_symbol: The str symbol of the index, such as `USDINR`.
    """

    def __init__(self, underlying_symbol: str = "USDINR"):
        """Stores the index whose future to look for.

        Args:
            underlying_symbol: The str symbol of the index.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Tries to build the contract and prints either the contract or the error.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        pair_expiries = currencies.CurrencyFutures.expiries(
            exchange="nse",
            underlying_symbol="USDINR",
        )
        if not pair_expiries:
            print("No USDINR futures are listed to borrow an expiry from.")
            return
        expiry_date = pair_expiries[0]
        try:
            contract = currencies.CurrencyIndexFutures(
                exchange="nse",
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
            )
        except exceptions.CurrencyIndexFuturesError as error:
            print(f"Not available today: {error}")
            return
        print(f"Found {contract.underlying_symbol} expiring {contract.expiry_date}")
        print(f"Last price: {contract.last_price}")


if __name__ == "__main__":
    CurrencyIndexFuturesLookup().run()
