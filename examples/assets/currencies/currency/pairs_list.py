"""List the currency pairs UBI carries on each exchange and the futures on each.

The program searches the nse and the bse for every currency pair, and for each pair prints how many futures and option expiries are listed on it, which shows at a glance where currency derivatives actually trade.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency/pairs_list.py
"""

from tradingmachine.assets import currencies


class CurrencyPairsList:
    """The currency pairs on two exchanges and the derivatives listed on each.

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
        """Searches each exchange and prints one line per pair.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        for exchange in self.exchanges:
            matches = currencies.Currency.search(
                exchange=exchange,
                term="",
                limit=200,
            )
            if matches is None:
                print(f"{exchange}: no currency pairs")
                continue
            print(f"{exchange}: {len(matches)} pairs")
            for symbol in matches["symbol"]:
                futures_expiries = currencies.CurrencyFutures.expiries(
                    exchange=exchange,
                    underlying_symbol=symbol,
                )
                option_expiries = currencies.CurrencyOption.expiries(
                    exchange=exchange,
                    underlying_symbol=symbol,
                )
                print(
                    f"    {symbol:<12} {len(futures_expiries)} futures expiries, "
                    f"{len(option_expiries)} option expiries"
                )


if __name__ == "__main__":
    CurrencyPairsList().run()
