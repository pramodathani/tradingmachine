"""Check whether any currency index future is listed, on either exchange.

The discovery calls fail cleanly on an empty segment: `expiries` returns an empty list and `contracts` returns None. The program asks both exchanges for every currency index future and reports what it finds, which is nothing today.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency_index_futures/discovery_is_empty.py
"""

from tradingmachine.assets import currencies


class CurrencyIndexFuturesDiscovery:
    """A search for currency index futures on the exchanges that trade currencies.

    Attributes:
        exchanges: The list of str exchanges to ask, `nse` and `bse`.
    """

    def __init__(self):
        """Stores the exchanges to ask.

        Raises:
            Nothing.
        """
        self.exchanges = [
            "nse",
            "bse",
        ]

    def run(self) -> None:
        """Asks each exchange for its contracts and prints the answers.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        for exchange in self.exchanges:
            rows = currencies.CurrencyIndexFutures.contracts(exchange=exchange)
            expiries = currencies.CurrencyIndexFutures.expiries(
                exchange=exchange,
                underlying_symbol="USDINR",
            )
            if rows is None:
                print(f"{exchange}: no contracts, and USDINR expiries are {expiries}")
            else:
                print(f"{exchange}: {len(rows)} contracts listed")


if __name__ == "__main__":
    CurrencyIndexFuturesDiscovery().run()
