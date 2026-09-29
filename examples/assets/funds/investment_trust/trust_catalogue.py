"""List every investment trust UBI carries on the nse with its last price and day change.

The program searches the nse's investment trusts segment with an empty term, which returns every trust, builds each one and prints its last price and its move since the previous close, sorted from the best day to the worst.

Typical usage example:

  .venv/bin/python examples/assets/funds/investment_trust/trust_catalogue.py
"""

from tradingmachine.assets import funds
from tradingmachine.unified_broker_interface import exceptions


class TrustCatalogue:
    """A table of the day's moves across every listed trust.

    Attributes:
        exchange: The str exchange whose trusts are listed.
    """

    def __init__(self):
        """Sets the exchange to list.

        Raises:
            Nothing.
        """
        self.exchange = "nse"

    def run(self) -> None:
        """Finds every trust, reads each one's prices and prints them sorted by the day's move.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        matches = funds.InvestmentTrust.search(exchange=self.exchange, term="")
        if matches is None:
            print(f"UBI carries no trusts on the {self.exchange}.")
            return
        print(f"{len(matches)} trusts on the {self.exchange}")
        rows = []
        for symbol in matches["symbol"]:
            row = self._read_trust(symbol)
            if row is not None:
                rows.append(row)
        rows.sort(key=self._change_of, reverse=True)
        for row in rows:
            print(
                f"{row['symbol']:12s} {row['last_price']:10.2f} {row['change']:7.2f}%"
            )

    def _read_trust(self, symbol: str) -> dict | None:
        """Builds one trust and reads its last price and previous close.

        Args:
            symbol: The str symbol of the trust.

        Returns:
            A dict with `symbol`, `last_price` and `change` in per cent, or None when the trust has no price or no broker quotes it.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request for a reason other than a missing quote.
        """
        trust = funds.InvestmentTrust(exchange=self.exchange, symbol=symbol)
        try:
            quote = trust.ohlc
        except exceptions.ServiceUnavailableError:
            print(f"{symbol}: no broker has a quote")
            return None
        last_price = quote.get("last_price")
        previous_close = quote.get("previous_close")
        if not last_price or not previous_close:
            print(f"{symbol}: no price")
            return None
        return {
            "symbol": symbol,
            "last_price": last_price,
            "change": (last_price / previous_close - 1) * 100,
        }

    @staticmethod
    def _change_of(row: dict) -> float:
        """Gives the day's move of one row, for sorting.

        Args:
            row: The dict row with a `change` key.

        Returns:
            The float change in per cent.

        Raises:
            Nothing.
        """
        return row["change"]


if __name__ == "__main__":
    TrustCatalogue().run()
