"""Print the strip of overnight MIBOR futures, one line per expiry.

The program lists every live futures contract on the overnight MIBOR index on the nse and prints each one's last price and the days it has left, which together show where the market expects the overnight rate to go.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income_index_futures/mibor_futures_strip.py
"""

from tradingmachine.assets import fixed_income


class MiborFuturesStrip:
    """The live futures on one fixed income index, soonest first.

    Attributes:
        exchange: The str exchange the futures trade on, such as `nse`.
        underlying_symbol: The str symbol of the index, such as `ONMIBOR`.
    """

    def __init__(self, exchange: str = "nse", underlying_symbol: str = "ONMIBOR"):
        """Stores the index whose futures to list.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index.

        Raises:
            Nothing.
        """
        self.exchange = exchange
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Builds each live contract and prints its line.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.FixedIncomeIndexFuturesError: A listed contract could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiries = fixed_income.FixedIncomeIndexFutures.expiries(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
        )
        if not expiries:
            print(f"No futures are listed on {self.underlying_symbol}.")
            return
        for expiry_date in expiries:
            contract = fixed_income.FixedIncomeIndexFutures(
                exchange=self.exchange,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
            )
            print(
                f"{expiry_date}: last {contract.last_price}, "
                f"{contract.days_to_expiry} days left, "
                f"{contract.expiry_kind} expiry"
            )


if __name__ == "__main__":
    MiborFuturesStrip().run()
