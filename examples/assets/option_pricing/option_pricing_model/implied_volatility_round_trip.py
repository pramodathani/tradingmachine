"""Recover a known volatility from the prices both pricing models give.

The program prices a NIFTY call with Black-Scholes and a crude oil put with Black-76 at volatilities chosen in advance, then hands each price back to the shared implied volatility search and prints how closely it finds the volatility it started from. It needs no market data.

Typical usage example:

  .venv/bin/python examples/assets/option_pricing/option_pricing_model/implied_volatility_round_trip.py
"""

from tradingmachine.assets import option_pricing


class ImpliedVolatilityRoundTrip:
    """A check that the implied volatility search undoes each pricing model.

    Attributes:
        risk_free_rate: The float annual risk-free rate every option is priced at.
        volatilities: The list of float volatilities each model is priced at and recovered from.
    """

    def __init__(self):
        """Sets the rate and the volatilities to test.

        Raises:
            Nothing.
        """
        self.risk_free_rate = 0.065
        self.volatilities = [
            0.08,
            0.15,
            0.35,
            0.80,
        ]

    def run(self) -> None:
        """Prices each option at each volatility and prints the volatility recovered from the price.

        Returns:
            None.

        Raises:
            ValueError: A price, strike or time to expiry is not above zero.
        """
        print("Black-Scholes, NIFTY call, spot 24000, strike 24100, 7 days")
        for volatility in self.volatilities:
            self._check_black_scholes(volatility)
        print("Black-76, crude oil put, future 5850, strike 5800, 20 days")
        for volatility in self.volatilities:
            self._check_black_76(volatility)

    def _check_black_scholes(self, volatility: float) -> None:
        """Prices the NIFTY call with Black-Scholes and prints the volatility the search recovers.

        Args:
            volatility: The float volatility to price at.

        Returns:
            None.

        Raises:
            ValueError: A price, strike or time to expiry is not above zero.
        """
        model = option_pricing.BlackScholes(
            underlying_price=24000.0,
            strike_price=24100.0,
            years_to_expiry=7 / 365,
            risk_free_rate=self.risk_free_rate,
            volatility=volatility,
            is_call=True,
        )
        recovered = option_pricing.BlackScholes.implied_volatility(
            premium=model.price,
            reference_price=24000.0,
            strike_price=24100.0,
            years_to_expiry=7 / 365,
            risk_free_rate=self.risk_free_rate,
            is_call=True,
        )
        self._print_row(volatility, model.price, recovered)

    def _check_black_76(self, volatility: float) -> None:
        """Prices the crude oil put with Black-76 and prints the volatility the search recovers.

        Args:
            volatility: The float volatility to price at.

        Returns:
            None.

        Raises:
            ValueError: A price, strike or time to expiry is not above zero.
        """
        model = option_pricing.Black76(
            forward_price=5850.0,
            strike_price=5800.0,
            years_to_expiry=20 / 365,
            risk_free_rate=self.risk_free_rate,
            volatility=volatility,
            is_call=False,
        )
        recovered = option_pricing.Black76.implied_volatility(
            premium=model.price,
            reference_price=5850.0,
            strike_price=5800.0,
            years_to_expiry=20 / 365,
            risk_free_rate=self.risk_free_rate,
            is_call=False,
        )
        self._print_row(volatility, model.price, recovered)

    def _print_row(
        self,
        volatility: float,
        premium: float,
        recovered: float | None,
    ) -> None:
        """Prints one line comparing the volatility used with the one recovered.

        Args:
            volatility: The float volatility the option was priced at.
            premium: The float price the model gave.
            recovered: The float volatility the search found, or None when it found none.

        Returns:
            None.

        Raises:
            Nothing.
        """
        if recovered is None:
            print(f"  {volatility:.2f}: premium {premium:.2f}, nothing recovered")
            return
        error = abs(recovered - volatility)
        print(
            f"  {volatility:.2f}: premium {premium:9.2f}, recovered {recovered:.6f}, error {error:.1e}"
        )


if __name__ == "__main__":
    ImpliedVolatilityRoundTrip().run()
