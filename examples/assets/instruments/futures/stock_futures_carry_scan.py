"""Scan a few stock futures for the richest and cheapest cost of carry.

The program lists the stock futures of the next monthly expiry, builds the future for each of a handful of well-known shares, and ranks them by the annual cost of carry their basis implies, which is how a cash-and-carry trader looks for futures that are dear or cheap against the share.

Typical usage example:

  .venv/bin/python examples/assets/instruments/futures/stock_futures_carry_scan.py
"""

import datetime

from tradingmachine.assets import equities


class StockFuturesCarryScan:
    """A ranking of stock futures by their implied cost of carry.

    Attributes:
        symbols: A list of str share symbols to scan.
    """

    def __init__(self):
        """Stores the shares to scan.

        Raises:
            Nothing.
        """
        self.symbols = [
            "RELIANCE",
            "INFY",
            "TCS",
            "HDFCBANK",
            "SBIN",
        ]

    def next_expiry(self) -> datetime.date:
        """Finds the first stock futures expiry with at least a week left, so the carry figure is meaningful.

        Returns:
            The datetime.date of the chosen expiry.

        Raises:
            ValueError: No stock futures expiry has a week left.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        contracts = equities.EquityFutures.contracts(exchange="nse")
        today = datetime.date.today()
        for expiry_date in sorted(set(contracts["expiry_date"])):
            if (expiry_date - today).days >= 7:
                return expiry_date
        raise ValueError(f"No stock futures expiry has a week left: {today=}")

    def run(self) -> None:
        """Prints the shares ranked by the carry of their future, highest first.

        Returns:
            None.

        Raises:
            ValueError: No stock futures expiry has a week left.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        expiry_date = self.next_expiry()
        print(f"Stock futures expiring {expiry_date}:")
        results = []
        for symbol in self.symbols:
            future = equities.EquityFutures(
                exchange="nse",
                underlying_symbol=symbol,
                expiry_date=expiry_date,
            )
            carry = future.cost_of_carry
            if carry is None:
                print(f"  {symbol}: a last price is missing")
                continue
            results.append((carry, symbol, future.basis_percent))
        results.sort(reverse=True)
        for carry, symbol, basis_percent in results:
            print(
                f"  {symbol:<10} basis {basis_percent:+.3f}%  carry {carry:+.2f}% a year"
            )


if __name__ == "__main__":
    StockFuturesCarryScan().run()
