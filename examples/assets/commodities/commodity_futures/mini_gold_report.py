"""Print a market report on the soonest mini gold future on the mcx.

The program builds the GOLDM contract with the soonest expiry, prints its live prices, its lot and what one lot is worth, and works out momentum and volatility from its daily candles, which commodity futures have in UBI.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity_futures/mini_gold_report.py
"""

from tradingmachine.assets import commodities


class MiniGoldReport:
    """A market report on one commodity futures contract.

    Attributes:
        contract: The tradingmachine.assets.commodities.CommodityFutures the report describes.
    """

    def __init__(self, underlying_symbol: str = "GOLDM"):
        """Builds the contract with the soonest expiry.

        Args:
            underlying_symbol: The str mcx symbol of the commodity, such as `GOLDM`.

        Raises:
            ValueError: No futures are listed on the commodity.
            tradingmachine.assets.exceptions.CommodityFuturesError: UBI has no such contract.
        """
        expiries = commodities.CommodityFutures.expiries(
            exchange="mcx",
            underlying_symbol=underlying_symbol,
        )
        if not expiries:
            raise ValueError(f"No futures are listed on {underlying_symbol}")
        self.contract = commodities.CommodityFutures(
            exchange="mcx",
            underlying_symbol=underlying_symbol,
            expiry_date=expiries[0],
        )

    def run(self) -> None:
        """Prints the live prices, the lot and the measures from candles.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        contract = self.contract
        print(f"{contract.underlying_symbol} expiring {contract.expiry_date}")
        print(f"Last price: {contract.last_price}")
        print(f"Best bid: {contract.best_bid}")
        print(f"Best offer: {contract.best_offer}")
        print(f"Lot: {contract.lot_size} units")
        print(f"One lot is worth: {contract.contract_value}")
        print(f"Open interest: {contract.open_interest}")
        strength_frame = contract.relative_strength_index(window=14, days=90)
        if strength_frame is None:
            print("UBI has no candles for this contract.")
            return
        latest_strength = strength_frame["rsi_14"].iloc[-1]
        print(f"Relative strength index (14 days): {latest_strength:.1f}")
        volatility = contract.annualised_volatility(days=90)
        if volatility is not None:
            print(f"Annualised volatility over 90 days: {volatility:.1%}")


if __name__ == "__main__":
    MiniGoldReport().run()
