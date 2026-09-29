"""Print every live commodity index future on the mcx, grouped by index.

The program lists the live contracts in the mcx commodity index futures segment and prints, for each index, the last price of each expiry, soonest first.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity_index_futures/index_futures_curve.py
"""

from tradingmachine.assets import commodities


class CommodityIndexFuturesCurve:
    """The live futures on every commodity index on one exchange.

    Attributes:
        exchange: The str exchange to list, such as `mcx`.
    """

    def __init__(self, exchange: str = "mcx"):
        """Stores the exchange to list.

        Args:
            exchange: The str exchange, such as `mcx`.

        Raises:
            Nothing.
        """
        self.exchange = exchange

    def run(self) -> None:
        """Lists the contracts and prints them index by index.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.CommodityIndexFuturesError: A listed contract could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        rows = commodities.CommodityIndexFutures.contracts(exchange=self.exchange)
        if rows is None:
            print(f"No commodity index futures on the {self.exchange}.")
            return
        rows = rows.sort_values(["underlying_symbol", "expiry_date"])
        current_symbol = None
        for row in rows.itertuples():
            if row.underlying_symbol != current_symbol:
                current_symbol = row.underlying_symbol
                print(current_symbol)
            contract = commodities.CommodityIndexFutures(
                exchange=self.exchange,
                underlying_symbol=row.underlying_symbol,
                expiry_date=row.expiry_date,
            )
            print(f"    {contract.expiry_date}: {contract.last_price}")


if __name__ == "__main__":
    CommodityIndexFuturesCurve().run()
