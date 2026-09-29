"""List the futures expiries written on each fixed income index, on both exchanges.

The program searches the nse and the bse for fixed income indices and prints, for each index, the expiries of the index futures listed on it.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income_index/index_futures_expiries.py
"""

from tradingmachine.assets import fixed_income


class RateIndexFuturesExpiries:
    """The index futures expiries on every fixed income index on two exchanges.

    Attributes:
        exchanges: The list of str exchanges to search, such as `nse` and `bse`.
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
        """Searches each exchange and prints the expiries per index.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        for exchange in self.exchanges:
            matches = fixed_income.FixedIncomeIndex.search(
                exchange=exchange,
                term="",
            )
            if matches is None:
                print(f"{exchange}: no fixed income index")
                continue
            for symbol in matches["symbol"]:
                expiries = fixed_income.FixedIncomeIndexFutures.expiries(
                    exchange=exchange,
                    underlying_symbol=symbol,
                )
                listed = []
                for expiry in expiries:
                    listed.append(expiry.isoformat())
                if not listed:
                    listed.append("none")
                print(f"{exchange} {symbol}: {', '.join(listed)}")


if __name__ == "__main__":
    RateIndexFuturesExpiries().run()
