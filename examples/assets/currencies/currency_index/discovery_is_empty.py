"""Check whether UBI carries any currency index yet.

Searching an empty segment returns None rather than raising, so a program can check for currency indices without catching anything. The program searches both exchanges with an empty term, which matches every row, and either prints what it finds or says that the segment is still empty.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency_index/discovery_is_empty.py
"""

from tradingmachine.assets import currencies


class CurrencyIndexDiscovery:
    """A search for currency indices on the exchanges that trade currencies.

    Attributes:
        exchanges: The list of str exchanges to search, `nse` and `bse`.
    """

    def __init__(self):
        """Stores the exchanges to search.

        Raises:
            Nothing.
        """
        self.exchanges = [
            "nse",
            "bse",
        ]

    def run(self) -> None:
        """Searches each exchange and prints the result.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        found_any = False
        for exchange in self.exchanges:
            matches = currencies.CurrencyIndex.search(
                exchange=exchange,
                term="",
                limit=200,
            )
            if matches is None:
                print(f"{exchange}: the currency indices segment is empty")
                continue
            found_any = True
            print(f"{exchange}: {matches['symbol'].tolist()}")
        if not found_any:
            print("UBI carries no currency index yet.")


if __name__ == "__main__":
    CurrencyIndexDiscovery().run()
