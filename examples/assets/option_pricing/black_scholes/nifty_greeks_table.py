"""Print a table of Black-Scholes prices and greeks across NIFTY strikes.

The program prices a call and a put at five strikes around a NIFTY level of 24000, a week from expiry at 12 per cent volatility, and prints the fair price, delta, gamma, theta, vega and rho of each, the way a broker's option chain shows them. It needs no market data.

Typical usage example:

  .venv/bin/python examples/assets/option_pricing/black_scholes/nifty_greeks_table.py
"""

from tradingmachine.assets import option_pricing


class NiftyGreeksTable:
    """A small option chain priced by Black-Scholes.

    Attributes:
        underlying_price: The float NIFTY level every option is priced from.
        years_to_expiry: The float time left until expiry, in years.
        risk_free_rate: The float annual risk-free rate.
        volatility: The float annual volatility.
        strike_prices: The list of float strikes to price.
    """

    def __init__(self):
        """Sets the market the chain is priced in.

        Raises:
            Nothing.
        """
        self.underlying_price = 24000.0
        self.years_to_expiry = 7 / 365
        self.risk_free_rate = 0.065
        self.volatility = 0.12
        self.strike_prices = [
            23800.0,
            23900.0,
            24000.0,
            24100.0,
            24200.0,
        ]

    def run(self) -> None:
        """Prints one row for the call and one for the put at every strike.

        Returns:
            None.

        Raises:
            ValueError: A price, strike, time to expiry or volatility is not above zero.
        """
        print("strike side    price   delta     gamma   theta   vega    rho")
        for strike_price in self.strike_prices:
            for is_call in [
                True,
                False,
            ]:
                self._print_row(strike_price, is_call)

    def _print_row(self, strike_price: float, is_call: bool) -> None:
        """Prices one option and prints its row.

        Args:
            strike_price: The float strike of the option.
            is_call: A bool that is True for a call and False for a put.

        Returns:
            None.

        Raises:
            ValueError: A price, strike, time to expiry or volatility is not above zero.
        """
        model = option_pricing.BlackScholes(
            underlying_price=self.underlying_price,
            strike_price=strike_price,
            years_to_expiry=self.years_to_expiry,
            risk_free_rate=self.risk_free_rate,
            volatility=self.volatility,
            is_call=is_call,
        )
        if is_call:
            side = "call"
        else:
            side = "put "
        print(
            f"{strike_price:6.0f} {side} {model.price:8.2f} {model.delta:7.4f} {model.gamma:9.6f} {model.theta:7.2f} {model.vega:6.2f} {model.rho:6.2f}"
        )


if __name__ == "__main__":
    NiftyGreeksTable().run()
