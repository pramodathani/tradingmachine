"""Check Black-Scholes against the greeks a live NIFTY option reports.

The program builds the at-the-money NIFTY call of the second listed expiry, asks it for its greeks, which it works out with Black-Scholes because its underlying is the index, and then prices the same option directly with `BlackScholes` from the index's last price, the option's implied volatility and the time left. The two sets of figures should agree to several decimal places.

Typical usage example:

  .venv/bin/python examples/assets/option_pricing/black_scholes/compare_with_live_option.py
"""

import datetime
import zoneinfo

from tradingmachine.assets import equities
from tradingmachine.assets import option_pricing


class CompareWithLiveOption:
    """A side-by-side check of a live option's greeks against the model itself.

    Attributes:
        index: The equities.EquityIndex for NIFTY.
        option: The equities.EquityIndexOption compared, the at-the-money call of the second expiry.
    """

    def __init__(self):
        """Reads the NIFTY level and builds the at-the-money call of the second expiry.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        expiries = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        strike_price = round(self.index.last_price / 50) * 50
        self.option = equities.EquityIndexOption(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiries[1],
            strike_price=strike_price,
            option_type="ce",
            underlying=self.index,
        )

    def run(self) -> None:
        """Prints the option's own greeks next to the ones BlackScholes gives for the same inputs.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        spot_price = self.index.last_price
        greeks = self.option.greeks(underlying_price=spot_price)
        if greeks is None:
            print(f"No greeks could be worked out for {self.option!r}")
            return
        model = option_pricing.BlackScholes(
            underlying_price=spot_price,
            strike_price=self.option.strike_price,
            years_to_expiry=self._years_to_expiry(),
            risk_free_rate=option_pricing.DEFAULT_RISK_FREE_RATE,
            volatility=greeks["volatility"],
            is_call=True,
        )
        print(repr(self.option))
        print(f"NIFTY {spot_price}, option last price {self.option.last_price}")
        print(f"Model named by the option: {greeks['model']}")
        print(f"Implied volatility: {greeks['volatility']:.4f}")
        print("measure   option.greeks()   BlackScholes")
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
