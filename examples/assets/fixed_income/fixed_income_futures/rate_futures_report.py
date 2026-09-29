"""Print the price of the soonest interest rate future on each underlying on the nse.

The program lists the live contracts in the nse's fixed income futures segment, keeps the soonest contract on each underlying, builds it from its row, and prints its last price, or says that no broker quotes it, its lot size and the days it has left. Keeping one contract per underlying keeps the number of quote requests small, because the brokers behind UBI limit how fast quotes can be read.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income_futures/rate_futures_report.py
"""

from tradingmachine.assets import fixed_income
from tradingmachine.unified_broker_interface import exceptions


class RateFuturesReport:
    """The live interest rate futures contracts on one exchange.

    Attributes:
        exchange: The str exchange to list, such as `nse`.
    """

    def __init__(self, exchange: str = "nse"):
        """Stores the exchange to list.

        Args:
            exchange: The str exchange, such as `nse`.

        Raises:
            Nothing.
        """
        self.exchange = exchange

    def run(self) -> None:
        """Lists the contracts and prints one line for the soonest on each underlying.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.FixedIncomeFuturesError: A listed contract could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        rows = fixed_income.FixedIncomeFutures.contracts(exchange=self.exchange)
        if rows is None:
            print(f"No live rate futures on the {self.exchange}.")
            return
        print(f"{len(rows)} live contracts on the {self.exchange}")
        seen_underlyings = []
        for row in rows.itertuples():
            if row.underlying_symbol in seen_underlyings:
                continue
            seen_underlyings.append(row.underlying_symbol)
            contract = fixed_income.FixedIncomeFutures(
                exchange=self.exchange,
                underlying_symbol=row.underlying_symbol,
                expiry_date=row.expiry_date,
            )
            try:
                price = contract.last_price
            except exceptions.ServiceUnavailableError:
                price = "no quote"
            print(
                f"{contract.underlying_symbol:<12} {contract.expiry_date} "
                f"price {price}, lot {contract.lot_size}, "
                f"{contract.days_to_expiry} days left"
            )


if __name__ == "__main__":
    RateFuturesReport().run()
