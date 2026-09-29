"""Value the bullion index call nearest the money off the index future.

The program builds the soonest MCXBULLDEX future, gives it to the call nearest its price on the matching option expiry as the underlying, and prints the call's premium and, when it has traded, its implied volatility and greeks under Black-76.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity_index_option/bullion_index_option_valuation.py
"""

from tradingmachine.assets import commodities
from tradingmachine.unified_broker_interface import exceptions


class BullionIndexOptionValuation:
    """A valuation of the call nearest the money on one commodity index.

    Attributes:
        underlying_symbol: The str mcx symbol of the index, such as `MCXBULLDEX`.
    """

    def __init__(self, underlying_symbol: str = "MCXBULLDEX"):
        """Stores the index whose option to value.

        Args:
            underlying_symbol: The str mcx symbol of the index.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Builds the future and the call, and prints the valuation.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.CommodityIndexFuturesError: UBI has no such future.
            tradingmachine.assets.exceptions.CommodityIndexOptionError: UBI has no such option.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        option_expiries = commodities.CommodityIndexOption.expiries(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
        )
        futures_expiries = commodities.CommodityIndexFutures.expiries(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
        )
        if not option_expiries or not futures_expiries:
            print(f"{self.underlying_symbol} lacks options or futures.")
            return
        expiry_date = option_expiries[0]
        future_expiry = futures_expiries[-1]
        for candidate in futures_expiries:
            if candidate >= expiry_date:
                future_expiry = candidate
                break
        future = commodities.CommodityIndexFutures(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
            expiry_date=future_expiry,
        )
        future_price = future.last_price
        strikes = commodities.CommodityIndexOption.strikes(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )
        strike_price = strikes[0]
        for strike in strikes:
            if abs(strike - future_price) < abs(strike_price - future_price):
                strike_price = strike
        option = commodities.CommodityIndexOption(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
            strike_price=strike_price,
            option_type="CE",
            underlying=future,
        )
        print(f"Future expiring {future_expiry} at {future_price}")
        print(f"Call at {strike_price} expiring {expiry_date}")
        try:
            premium = option.last_price
        except exceptions.ServiceUnavailableError:
            print("The call has no quote.")
            return
        print(f"Premium: {premium}")
        greeks = option.greeks()
        if greeks is None:
            print("No greeks, because the call has not traded.")
            return
        print(f"Model: {greeks['model']}")
        print(f"Implied volatility: {greeks['volatility']:.1%}")
        print(f"Delta: {greeks['delta']:.3f}")


if __name__ == "__main__":
    BullionIndexOptionValuation().run()
