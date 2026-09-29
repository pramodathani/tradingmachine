"""Value the crude oil call nearest the money with Black-76.

An MCX option settles into a future, so the library prices it off the future on the same commodity that expires first on or after it. The program picks the CRUDEOIL call nearest that future's price on the soonest expiry, and prints its premium, the future it is priced off, and its implied volatility and greeks.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity_option/crude_option_valuation.py
"""

from tradingmachine.assets import commodities


class CrudeOptionValuation:
    """A valuation of the call nearest the money on one commodity.

    Attributes:
        underlying_symbol: The str mcx symbol of the commodity, such as `CRUDEOIL`.
    """

    def __init__(self, underlying_symbol: str = "CRUDEOIL"):
        """Stores the commodity whose option to value.

        Args:
            underlying_symbol: The str mcx symbol of the commodity.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Chooses the option, builds it and prints its valuation.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.CommodityOptionError: UBI has no such option.
            tradingmachine.assets.exceptions.UnderlyingError: The option's future cannot be found.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiries = commodities.CommodityOption.expiries(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
        )
        if not expiries:
            print(f"No options are listed on {self.underlying_symbol}.")
            return
        strikes = commodities.CommodityOption.strikes(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiries[0],
        )
        probe = commodities.CommodityOption(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiries[0],
            strike_price=strikes[0],
            option_type="CE",
        )
        future = probe.underlying
        future_price = future.last_price
        strike_price = strikes[0]
        for strike in strikes:
            if abs(strike - future_price) < abs(strike_price - future_price):
                strike_price = strike
        option = commodities.CommodityOption(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiries[0],
            strike_price=strike_price,
            option_type="CE",
            underlying=future,
        )
        print(f"Call at {strike_price} expiring {option.expiry_date}")
        print(f"Priced off the future expiring {future.expiry_date} at {future_price}")
        print(f"Premium: {option.last_price}, per lot {option.premium_per_lot}")
        print(f"Time value: {option.time_value}")
        greeks = option.greeks()
        if greeks is None:
            print("No greeks, because the prices needed are not known.")
            return
        print(f"Model: {greeks['model']}")
        print(f"Implied volatility: {greeks['volatility']:.1%}")
        print(f"Delta: {greeks['delta']:.3f}")
        print(f"Theta per day: {greeks['theta']:.2f}")


if __name__ == "__main__":
    CrudeOptionValuation().run()
