"""Check Black-76 against the greeks a live NIFTY option reports when it is priced off a future.

The program builds the at-the-money NIFTY call of the second listed expiry and gives it, as its underlying, the NIFTY future that expires first on or after the option. That makes the option work out its greeks with Black-76. The program then prices the same option directly with `Black76` from the future's last price, the option's implied volatility and the time left, and prints both sets of figures side by side.

Typical usage example:

  .venv/bin/python examples/assets/option_pricing/black76/compare_with_live_option.py
"""

import datetime
import zoneinfo

from tradingmachine.assets import equities
from tradingmachine.assets import option_pricing


class CompareWithLiveOption:
    """A side-by-side check of a live option's Black-76 greeks against the model itself.

    Attributes:
        future: The equities.EquityIndexFutures the option is priced off.
        option: The equities.EquityIndexOption compared, the at-the-money call of the second expiry.
    """

    def __init__(self):
        """Picks the option's expiry, the future that covers it, and the at-the-money strike.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        option_expiries = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        option_expiry = option_expiries[1]
        future_expiries = equities.EquityIndexFutures.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        future_expiry = None
        for expiry_date in future_expiries:
            if expiry_date >= option_expiry:
                future_expiry = expiry_date
                break
        self.future = equities.EquityIndexFutures(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=future_expiry,
        )
        strike_price = round(self.future.last_price / 50) * 50
        self.option = equities.EquityIndexOption(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=option_expiry,
            strike_price=strike_price,
            option_type="ce",
            underlying=self.future,
        )

    def run(self) -> None:
        """Prints the option's own greeks next to the ones Black76 gives for the same inputs.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        forward_price = self.future.last_price
        greeks = self.option.greeks(underlying_price=forward_price)
        if greeks is None:
            print(f"No greeks could be worked out for {self.option!r}")
            return
        model = option_pricing.Black76(
            forward_price=forward_price,
            strike_price=self.option.strike_price,
            years_to_expiry=self._years_to_expiry(),
            risk_free_rate=option_pricing.DEFAULT_RISK_FREE_RATE,
            volatility=greeks["volatility"],
            is_call=True,
        )
        print(repr(self.option))
        print(f"Priced off {self.future!r} at {forward_price}")
        print(f"Model named by the option: {greeks['model']}")
        print(f"Implied volatility: {greeks['volatility']:.4f}")
        print("measure   option.greeks()   Black76")
        self._print_pair("price", greeks["price"], model.price)
        self._print_pair("delta", greeks["delta"], model.delta)
        self._print_pair("gamma", greeks["gamma"], model.gamma)
        self._print_pair("theta", greeks["theta"], model.theta)
        self._print_pair("vega", greeks["vega"], model.vega)
        self._print_pair("rho", greeks["rho"], model.rho)

    def _print_pair(self, name: str, from_option: float, from_model: float) -> None:
        """Prints one measure from both sources.

        Args:
            name: The str name of the measure.
            from_option: The float value the option's greeks reported.
            from_model: The float value the model gave.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(f"{name:8s} {from_option:16.6f} {from_model:14.6f}")

    def _years_to_expiry(self) -> float:
        """Works out the time from now until 15:30 India time on the expiry date, as the option does.

        Returns:
            The float number of years left.

        Raises:
            Nothing.
        """
        india = zoneinfo.ZoneInfo("Asia/Kolkata")
        expiry_moment = datetime.datetime.combine(
            self.option.expiry_date,
            datetime.time(15, 30),
            india,
        )
        now = datetime.datetime.now(india)
        seconds_left = (expiry_moment - now).total_seconds()
        return seconds_left / (365 * 24 * 60 * 60)


if __name__ == "__main__":
    CompareWithLiveOption().run()
