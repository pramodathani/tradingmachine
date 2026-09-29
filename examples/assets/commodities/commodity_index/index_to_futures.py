"""Read a commodity index's level from its soonest future.

An mcx commodity index has no quote of its own, but some of them have futures that do. The program goes through the mcx indices, and for each one with futures listed, prints the soonest contract's last price as the market's view of the index.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity_index/index_to_futures.py
"""

from tradingmachine.assets import commodities


class CommodityIndexThroughFutures:
    """The soonest future on each mcx commodity index that has one.

    Attributes:
        exchange: The str exchange to search, such as `mcx`.
    """

    def __init__(self, exchange: str = "mcx"):
        """Stores the exchange to search.

        Args:
            exchange: The str exchange, such as `mcx`.

        Raises:
            Nothing.
        """
        self.exchange = exchange

    def run(self) -> None:
        """Goes through the indices and prints the soonest future on each.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.CommodityIndexFuturesError: A listed contract could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        matches = commodities.CommodityIndex.search(
            exchange=self.exchange,
            term="",
            limit=200,
        )
        if matches is None:
            print(f"No commodity index on the {self.exchange}.")
            return
        for symbol in matches["symbol"]:
            index = commodities.CommodityIndex(exchange=self.exchange, symbol=symbol)
            expiries = commodities.CommodityIndexFutures.expiries(
                exchange=self.exchange,
                underlying_symbol=index.symbol,
            )
            if not expiries:
                print(f"{symbol}: no futures listed")
                continue
            contract = commodities.CommodityIndexFutures(
                exchange=self.exchange,
                underlying_symbol=index.symbol,
                expiry_date=expiries[0],
                underlying=index,
            )
            print(f"{symbol}: future expiring {expiries[0]} at {contract.last_price}")


if __name__ == "__main__":
    CommodityIndexThroughFutures().run()
