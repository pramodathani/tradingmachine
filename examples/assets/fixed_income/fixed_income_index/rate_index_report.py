"""Report on the nse's fixed income indices and the gap in their quotes.

The program lists every fixed income index on the nse, builds each one, and prints its identity. Asking for a level raises ServiceUnavailableError, because no broker that serves quotes carries a rate index, so the program catches that and says so.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income_index/rate_index_report.py
"""

from tradingmachine.assets import fixed_income
from tradingmachine.unified_broker_interface import exceptions


class RateIndexReport:
    """A report on every fixed income index on one exchange.

    Attributes:
        exchange: The str exchange to report on, such as `nse`.
    """

    def __init__(self, exchange: str = "nse"):
        """Stores the exchange to report on.

        Args:
            exchange: The str exchange, such as `nse`.

        Raises:
            Nothing.
        """
        self.exchange = exchange

    def run(self) -> None:
        """Lists the indices and prints what is known of each.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.FixedIncomeIndexError: A listed index could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        matches = fixed_income.FixedIncomeIndex.search(
            exchange=self.exchange,
            term="",
        )
        if matches is None:
            print(f"No fixed income index on the {self.exchange}.")
            return
        for symbol in matches["symbol"]:
            index = fixed_income.FixedIncomeIndex(
                exchange=self.exchange,
                symbol=symbol,
            )
            print(f"{index.symbol}: {index.segment}, id {index.instrument_id}")
            try:
                print(f"    level {index.last_price}")
            except exceptions.ServiceUnavailableError:
                print("    no quote, because no broker that serves quotes carries it")


if __name__ == "__main__":
    RateIndexReport().run()
