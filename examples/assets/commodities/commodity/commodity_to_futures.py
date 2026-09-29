"""Go from a few commodities to the price of the soonest future on each.

A commodity has no price of its own, so the way to see where it trades is its nearest future. The program builds each commodity, lists the futures expiries written on it, and prints the soonest contract's last price and lot size.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity/commodity_to_futures.py
"""

from tradingmachine.assets import commodities


class CommodityNearestFutures:
    """The soonest future on each of a few mcx commodities.

    Attributes:
        symbols: The list of str mcx commodity symbols to report on.
    """

    def __init__(self):
        """Stores the commodities to report on.

        Raises:
            Nothing.
        """
        self.symbols = [
            "GOLDM",
            "SILVERM",
            "CRUDEOILM",
            "NATGASMINI",
        ]

    def run(self) -> None:
        """Builds each commodity and prints its soonest future.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.CommodityError: A commodity is not in UBI.
            tradingmachine.assets.exceptions.CommodityFuturesError: A listed contract could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        for symbol in self.symbols:
            commodity = commodities.Commodity(exchange="mcx", symbol=symbol)
            expiries = commodities.CommodityFutures.expiries(
                exchange="mcx",
                underlying_symbol=commodity.symbol,
            )
            if not expiries:
                print(f"{symbol}: no futures listed")
                continue
            contract = commodities.CommodityFutures(
                exchange="mcx",
                underlying_symbol=commodity.symbol,
                expiry_date=expiries[0],
            )
            print(
                f"{symbol}: {len(expiries)} expiries, soonest {expiries[0]} "
                f"at {contract.last_price}, lot {contract.lot_size}"
            )


if __name__ == "__main__":
    CommodityNearestFutures().run()
