"""Measure the volatility smile of the next NIFTY weekly expiry from live prices.

The program finds the second NIFTY option expiry, so that it never works on a contract expiring today, reads the index's last price, and for seven strikes around the money builds the out-of-the-money option, reads its last price and asks Black-Scholes for the volatility that premium implies. The resulting table shows how implied volatility changes with the strike.

Typical usage example:

  .venv/bin/python examples/assets/option_pricing/option_pricing_model/live_nifty_volatility_smile.py
"""

import datetime
import zoneinfo

from tradingmachine.assets import equities
from tradingmachine.assets import option_pricing


class LiveNiftyVolatilitySmile:
    """A table of NIFTY implied volatilities across strikes for one expiry.

    Attributes:
        index: The equities.EquityIndex for NIFTY.
        expiry_date: The datetime.date of the expiry measured.
        strike_step: The float distance between the strikes measured.
        risk_free_rate: The float annual risk-free rate used in the search.
    """

    def __init__(self):
        """Reads the NIFTY index and picks the second expiry listed.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        expiries = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        self.expiry_date = expiries[1]
        self.strike_step = 100.0
        self.risk_free_rate = option_pricing.DEFAULT_RISK_FREE_RATE

    def run(self) -> None:
        """Prints the implied volatility of the out-of-the-money option at seven strikes.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        spot_price = self.index.last_price
        years_to_expiry = self._years_to_expiry()
        middle_strike = round(spot_price / self.strike_step) * self.strike_step
        print(f"NIFTY {spot_price}, expiry {self.expiry_date}")
        print(f"Years to expiry: {years_to_expiry:.5f}")
        for step in range(-3, 4):
            strike_price = middle_strike + step * self.strike_step
            self._print_strike(spot_price, strike_price, years_to_expiry)

    def _print_strike(
        self,
        spot_price: float,
        strike_price: float,
        years_to_expiry: float,
    ) -> None:
        """Prints the implied volatility of the out-of-the-money option at one strike.

        Args:
            spot_price: The float last price of the index.
            strike_price: The float strike to measure.
            years_to_expiry: The float time left until expiry, in years.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        if strike_price >= spot_price:
            option_type = "ce"
        else:
            option_type = "pe"
        option = equities.EquityIndexOption(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=self.expiry_date,
            strike_price=strike_price,
            option_type=option_type,
        )
        premium = option.last_price
        if premium is None:
            print(f"{strike_price:.0f} {option_type}: no last price")
            return
        volatility = option_pricing.BlackScholes.implied_volatility(
            premium=premium,
            reference_price=spot_price,
            strike_price=strike_price,
            years_to_expiry=years_to_expiry,
            risk_free_rate=self.risk_free_rate,
            is_call=option_type == "ce",
        )
        if volatility is None:
            print(f"{strike_price:.0f} {option_type}: premium {premium}, none")
            return
        print(
            f"{strike_price:.0f} {option_type}: premium {premium:8.2f}, implied volatility {volatility * 100:.2f} per cent"
        )

    def _years_to_expiry(self) -> float:
        """Works out the time from now until 15:30 India time on the expiry date.

        Returns:
            The float number of years left.

        Raises:
            Nothing.
        """
        india = zoneinfo.ZoneInfo("Asia/Kolkata")
        expiry_moment = datetime.datetime.combine(
            self.expiry_date,
            datetime.time(15, 30),
            india,
        )
        now = datetime.datetime.now(india)
        seconds_left = (expiry_moment - now).total_seconds()
        return seconds_left / (365 * 24 * 60 * 60)


if __name__ == "__main__":
    LiveNiftyVolatilitySmile().run()
