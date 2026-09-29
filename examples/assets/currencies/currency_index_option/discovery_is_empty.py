"""Check whether any currency index option is listed, on either exchange.

The discovery calls fail cleanly on an empty segment: `expiries` and `strikes` return empty lists and `chain` returns None. The program asks both exchanges for dollar index option expiries, strikes and a chain, and reports what it finds, which is nothing today.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency_index_option/discovery_is_empty.py
"""

from tradingmachine.assets import currencies


class CurrencyIndexOptionDiscovery:
    """A search for currency index options on the exchanges that trade currencies.

    Attributes:
        underlying_symbol: The str symbol of the index, such as `USDINR`.
        exchanges: The list of str exchanges to ask, `nse` and `bse`.
    """

    def __init__(self, underlying_symbol: str = "USDINR"):
        """Stores the index and the exchanges to ask.

        Args:
            underlying_symbol: The str symbol of the index.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol
        self.exchanges = [
            "nse",
            "bse",
        ]

    def run(self) -> None:
        """Asks each exchange for expiries, strikes and a chain, and prints the answers.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        for exchange in self.exchanges:
            expiries = currencies.CurrencyIndexOption.expiries(
                exchange=exchange,
                underlying_symbol=self.underlying_symbol,
            )
            if expiries:
                print(f"{exchange}: options listed for {expiries}")
                continue
            pair_expiries = currencies.CurrencyOption.expiries(
                exchange="nse",
                underlying_symbol="USDINR",
            )
            if not pair_expiries:
                print(f"{exchange}: no expiries listed")
                continue
            strikes = currencies.CurrencyIndexOption.strikes(
                exchange=exchange,
                underlying_symbol=self.underlying_symbol,
                expiry_date=pair_expiries[0],
            )
            chain = currencies.CurrencyIndexOption.chain(
                exchange=exchange,
                underlying_symbol=self.underlying_symbol,
                expiry_date=pair_expiries[0],
            )
            print(f"{exchange}: expiries {expiries}, strikes {strikes}, chain {chain}")


if __name__ == "__main__":
    CurrencyIndexOptionDiscovery().run()
