"""Price a call and a put on a commodity future with Black-76 and show how they respond.

The program prices options on a future trading at 9125 with seventeen days to run at 59 per cent volatility, prints the price and greeks of each, and then shows how the call's price moves when the future, the volatility and the time left each change on their own. It needs no market data.

Typical usage example:

  .venv/bin/python examples/assets/option_pricing/black76/commodity_option_greeks.py
"""

from tradingmachine.assets import option_pricing


class CommodityOptionGreeks:
    """A Black-76 report on options written on one future.

    Attributes:
        forward_price: The float price of the future.
        strike_price: The float strike of both options.
        days_to_expiry: The int number of calendar days left.
        risk_free_rate: The float annual risk-free rate.
        volatility: The float annual volatility of the future.
    """

    def __init__(self):
        """Sets the future and the options to price.

        Raises:
            Nothing.
        """
        self.forward_price = 9125.0
        self.strike_price = 9100.0
        self.days_to_expiry = 17
        self.risk_free_rate = 0.065
        self.volatility = 0.59

    def run(self) -> None:
        """Prints the greeks of the call and the put, then the call's price under three changes.

        Returns:
            None.

        Raises:
            ValueError: A price, strike, time to expiry or volatility is not above zero.
        """
        for is_call in [
            True,
            False,
        ]:
            model = self._model(
                self.forward_price,
                self.volatility,
                self.days_to_expiry,
                is_call,
            )
            self._print_greeks(model)
        base = self._model(
            self.forward_price,
            self.volatility,
            self.days_to_expiry,
            True,
        )
        higher_future = self._model(
            self.forward_price + 100,
            self.volatility,
            self.days_to_expiry,
            True,
        )
        higher_volatility = self._model(
            self.forward_price,
            self.volatility + 0.05,
            self.days_to_expiry,
            True,
        )
        a_week_later = self._model(
            self.forward_price,
            self.volatility,
            self.days_to_expiry - 7,
            True,
        )
        print(f"Call price now: {base.price:.2f}")
        print(f"Future 100 higher: {higher_future.price:.2f}")
        print(f"Volatility 5 points higher: {higher_volatility.price:.2f}")
        print(f"A week later: {a_week_later.price:.2f}")

    def _model(
        self,
        forward_price: float,
        volatility: float,
        days_to_expiry: int,
        is_call: bool,
    ) -> option_pricing.Black76:
        """Builds one Black-76 model at the strike and rate this report uses.

        Args:
            forward_price: The float price of the future.
            volatility: The float annual volatility.
            days_to_expiry: The int number of calendar days left.
            is_call: A bool that is True for a call and False for a put.

        Returns:
            The option_pricing.Black76 model.

        Raises:
            ValueError: A price, strike, time to expiry or volatility is not above zero.
        """
        return option_pricing.Black76(
            forward_price=forward_price,
            strike_price=self.strike_price,
            years_to_expiry=days_to_expiry / 365,
            risk_free_rate=self.risk_free_rate,
            volatility=volatility,
            is_call=is_call,
        )

    def _print_greeks(self, model: option_pricing.Black76) -> None:
        """Prints the price and the five greeks of one option.

        Args:
            model: The option_pricing.Black76 model to report.

        Returns:
            None.

        Raises:
            Nothing.
        """
        if model.is_call:
            print("Call")
        else:
            print("Put")
        print(f"  price {model.price:.2f}")
        print(f"  delta {model.delta:.4f}")
        print(f"  gamma {model.gamma:.6f}")
        print(f"  theta {model.theta:.2f} per day")
        print(f"  vega  {model.vega:.2f} per point")
        print(f"  rho   {model.rho:.4f} per point")


if __name__ == "__main__":
    CommodityOptionGreeks().run()
