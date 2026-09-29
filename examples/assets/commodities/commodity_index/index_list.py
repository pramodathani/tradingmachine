"""List the mcx commodity indices and show that they have no quote.

The program searches the mcx for commodity indices, builds each one, and tries to read its level. No tick stream resolves a commodity index, so every read raises ServiceUnavailableError, which the program catches and reports.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity_index/index_list.py
"""

from tradingmachine.assets import commodities
from tradingmachine.unified_broker_interface import exceptions


class CommodityIndexList:
    """The commodity indices one exchange publishes.

    Attributes:
        exchange: The str exchange to list, `mcx` or `ncdex`.
    """

    def __init__(self, exchange: str = "mcx"):
        """Stores the exchange to list.

        Args:
            exchange: The str exchange, `mcx` or `ncdex`.

        Raises:
            Nothing.
        """
        self.exchange = exchange

    def run(self) -> None:
        """Lists the indices and prints what each one gives.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.CommodityIndexError: A listed index could not be built.
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
        print(f"{len(matches)} commodity indices on the {self.exchange}")
        for symbol in matches["symbol"]:
            index = commodities.CommodityIndex(exchange=self.exchange, symbol=symbol)
            try:
                level = index.last_price
            except exceptions.ServiceUnavailableError:
                level = "no quote"
            print(f"{index.symbol:<14} {level}")


if __name__ == "__main__":
    CommodityIndexList().run()
