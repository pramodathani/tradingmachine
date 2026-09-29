"""Value an option on an interest rate underlying off the future it settles into.

The program picks the soonest option expiry on the 6.33 per cent government security of 2035 and the call whose strike is nearest the price of the future the option is priced off. It prints the option's premium, the future's price and, when the option has traded, its implied volatility and greeks under Black-76.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income_option/rate_option_valuation.py
"""

from tradingmachine.assets import fixed_income


class RateOptionValuation:
    """A valuation of the call nearest the money on one interest rate underlying.

    Attributes:
        underlying_symbol: The str rate code of the security, such as `633GS2035`.
    """

    def __init__(self, underlying_symbol: str = "633GS2035"):
        """Stores the security whose option to value.

        Args:
            underlying_symbol: The str rate code of the security.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Chooses the option, builds it and prints its valuation.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.FixedIncomeOptionError: UBI has no such option.
            tradingmachine.assets.exceptions.UnderlyingError: The option's future cannot be found.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiries = fixed_income.FixedIncomeOption.expiries(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        if not expiries:
            print(f"No options are listed on {self.underlying_symbol}.")
            return
        strikes = fixed_income.FixedIncomeOption.strikes(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiries[0],
        )
        first_option = fixed_income.FixedIncomeOption(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiries[0],
            strike_price=strikes[0],
            option_type="CE",
        )
        future_price = first_option.underlying_price
        print(f"Priced off the future at {future_price}")
        strike_price = strikes[0]
        if future_price is not None:
            for strike in strikes:
                if abs(strike - future_price) < abs(strike_price - future_price):
                    strike_price = strike
        option = fixed_income.FixedIncomeOption(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiries[0],
            strike_price=strike_price,
            option_type="CE",
        )
        print(f"Call at {strike_price} expiring {option.expiry_date}")
        print(f"Premium: {option.last_price}")
        print(f"Intrinsic value: {option.intrinsic_value}")
        greeks = option.greeks()
        if greeks is None:
            print("No greeks, because the prices needed are not known.")
            return
        print(f"Model: {greeks['model']}")
        print(f"Implied volatility: {greeks['volatility']:.1%}")
        print(f"Delta: {greeks['delta']:.3f}")


if __name__ == "__main__":
    RateOptionValuation().run()
