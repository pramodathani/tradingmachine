"""Check whether any option on a fixed income index is listed, on either exchange.

The discovery calls fail cleanly rather than raising when a segment is empty: `expiries` returns an empty list and `chain` returns None. The program asks both exchanges for the overnight MIBOR option expiries and chain, and reports what it finds, which is nothing today.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income_index_option/discovery_is_empty.py
"""

from tradingmachine.assets import fixed_income


class RateIndexOptionDiscovery:
    """A search for options on one fixed income index across two exchanges.

    Attributes:
        underlying_symbol: The str symbol of the index, such as `ONMIBOR`.
        exchanges: The list of str exchanges to ask, such as `nse` and `bse`.
    """

    def __init__(self, underlying_symbol: str = "ONMIBOR"):
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
        """Asks each exchange for expiries and a chain, and prints the answers.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        for exchange in self.exchanges:
            expiries = fixed_income.FixedIncomeIndexOption.expiries(
                exchange=exchange,
                underlying_symbol=self.underlying_symbol,
            )
            if expiries:
                chain = fixed_income.FixedIncomeIndexOption.chain(
                    exchange=exchange,
                    underlying_symbol=self.underlying_symbol,
                    expiry_date=expiries[0],
                )
                print(f"{exchange}: {len(chain)} options expiring {expiries[0]}")
                continue
            chain = fixed_income.FixedIncomeIndexOption.chain(
                exchange=exchange,
                underlying_symbol=self.underlying_symbol,
                expiry_date="2026-12-31",
            )
            print(f"{exchange}: no expiries listed, and the chain is {chain}")


if __name__ == "__main__":
    RateIndexOptionDiscovery().run()
