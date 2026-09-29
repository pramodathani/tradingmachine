"""Try to build a currency index and handle the error UBI gives today.

UBI holds no rows in its currency indices segment on any exchange, so every lookup fails with CurrencyIndexError. The program asks the nse and the bse for a dollar index, catches the error for each, and prints it, so the same code will simply start working the day UBI carries one.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency_index/lookup_error_handled.py
"""

from tradingmachine.assets import currencies
from tradingmachine.assets import exceptions


class CurrencyIndexLookup:
    """An attempt to build one currency index on each exchange that trades currencies.

    Attributes:
        symbol: The str symbol of the index to look for, such as `USDINR`.
        exchanges: The list of str exchanges to ask, `nse` and `bse`.
    """

    def __init__(self, symbol: str = "USDINR"):
        """Stores the index to look for and the exchanges to ask.

        Args:
            symbol: The str symbol of the index.

        Raises:
            Nothing.
        """
        self.symbol = symbol
        self.exchanges = [
            "nse",
            "bse",
        ]

    def run(self) -> None:
        """Tries each exchange and prints either the index or the error.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        for exchange in self.exchanges:
            try:
                index = currencies.CurrencyIndex(exchange=exchange, symbol=self.symbol)
            except exceptions.CurrencyIndexError as error:
                print(f"{exchange}: not available today: {error}")
                continue
            print(f"{exchange}: found {index.symbol}, id {index.instrument_id}")


if __name__ == "__main__":
    CurrencyIndexLookup().run()
