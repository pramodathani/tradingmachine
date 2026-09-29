"""Ask a gold future for its underlying and handle the UnderlyingError.

A commodity future's underlying is physical gold, which has no price in UBI, and UBI links the contract to no underlying, so `underlying` raises UnderlyingError unless one was given when the contract was built. The program catches it and reports the future's own last price and days to expiry, which do not need the underlying.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/underlying_error/price_a_gold_future_without_its_underlying.py
"""

from tradingmachine.assets import commodities
from tradingmachine.assets import exceptions


class GoldFutureReport:
    """A short report on the nearest GOLDM futures contract.

    Attributes:
        contract: The tradingmachine.assets.commodities.CommodityFutures reported on, or None before run.
    """

    def __init__(self):
        """Creates the report with no contract yet.

        Raises:
            Nothing.
        """
        self.contract = None

    def run(self) -> None:
        """Builds the nearest GOLDM future, asks for its underlying and prints what is known.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.CommodityFuturesError: UBI does not know the contract.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date = commodities.CommodityFutures.expiries("mcx", "GOLDM")[0]
        self.contract = commodities.CommodityFutures(
            exchange="mcx",
            underlying_symbol="GOLDM",
            expiry_date=expiry_date,
        )
        print(f"Contract: {self.contract!r}")
        try:
            underlying = self.contract.underlying
        except exceptions.UnderlyingError as error:
            print(f"UnderlyingError: {error}")
            underlying = None
        if underlying is not None:
            print(f"Underlying: {underlying!r}")
        print(f"Days to expiry: {self.contract.days_to_expiry}")
        print(f"Last price: {self.contract.last_price}")


if __name__ == "__main__":
    GoldFutureReport().run()
