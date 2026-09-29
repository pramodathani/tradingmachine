"""Print a report on the soonest bullion index future on the mcx.

The program builds the soonest MCXBULLDEX future and prints its price, its lot and what one lot is worth, its order book, and the last few daily closes from its candles.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity_index_futures/bullion_index_futures_report.py
"""

from tradingmachine.assets import commodities


class BullionIndexFuturesReport:
    """A report on one commodity index futures contract.

    Attributes:
        contract: The tradingmachine.assets.commodities.CommodityIndexFutures the report describes.
    """

    def __init__(self, underlying_symbol: str = "MCXBULLDEX"):
        """Builds the contract with the soonest expiry.

        Args:
            underlying_symbol: The str mcx symbol of the index, such as `MCXBULLDEX`.

        Raises:
            ValueError: No futures are listed on the index.
            tradingmachine.assets.exceptions.CommodityIndexFuturesError: UBI has no such contract.
        """
        expiries = commodities.CommodityIndexFutures.expiries(
            exchange="mcx",
            underlying_symbol=underlying_symbol,
        )
        if not expiries:
            raise ValueError(f"No futures are listed on {underlying_symbol}")
        self.contract = commodities.CommodityIndexFutures(
            exchange="mcx",
            underlying_symbol=underlying_symbol,
            expiry_date=expiries[0],
        )

    def run(self) -> None:
        """Prints the live values and the recent closes.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        contract = self.contract
        print(f"{contract.underlying_symbol} future expiring {contract.expiry_date}")
        print(f"Days to expiry: {contract.days_to_expiry}")
        print(f"Last price: {contract.last_price}")
        print(f"Lot: {contract.lot_size}, one lot worth {contract.contract_value}")
        print(f"Best bid: {contract.best_bid}")
        print(f"Best offer: {contract.best_offer}")
        candles = contract.prices(days=14)
        if candles is None:
            print("UBI has no recent candles for this contract.")
            return
        for row in candles.tail(5).itertuples():
            print(f"{row.datetime.date()}: close {row.close}")


if __name__ == "__main__":
    BullionIndexFuturesReport().run()
