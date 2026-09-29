"""Show that a currency pair has no quote, and read its rate from the nearest future.

A currency pair such as USDINR on the nse is the exchange's reference record for the underlying rather than something that trades, so reading its last price raises ServiceUnavailableError. The program builds the pair, catches that error, and prints the soonest future's last price instead.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency/pair_has_no_quote.py
"""

from tradingmachine.assets import currencies
from tradingmachine.unified_broker_interface import exceptions


class CurrencyPairRate:
    """The rate of one currency pair, read from its soonest future.

    Attributes:
        pair: The tradingmachine.assets.currencies.Currency whose rate to read.
    """

    def __init__(self, symbol: str = "USDINR"):
        """Looks the pair up on the nse.

        Args:
            symbol: The str symbol of the pair, such as `USDINR`.

        Raises:
            tradingmachine.assets.exceptions.CurrencyError: UBI has no such pair on the nse.
        """
        self.pair = currencies.Currency(exchange="nse", symbol=symbol)

    def run(self) -> None:
        """Tries the pair's own quote, then prints the soonest future's price.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.CurrencyFuturesError: UBI has no such contract.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        print(f"{self.pair.symbol}: {self.pair.segment}, {self.pair.shape}")
        try:
            print(f"Last price: {self.pair.last_price}")
        except exceptions.ServiceUnavailableError as error:
            print(f"The pair itself has no quote: {error}")
        expiries = currencies.CurrencyFutures.expiries(
            exchange="nse",
            underlying_symbol=self.pair.symbol,
        )
        if not expiries:
            print("No futures are listed on the pair.")
            return
        contract = currencies.CurrencyFutures(
            exchange="nse",
            underlying_symbol=self.pair.symbol,
            expiry_date=expiries[0],
        )
        print(f"Future expiring {contract.expiry_date}: {contract.last_price}")


if __name__ == "__main__":
    CurrencyPairRate().run()
