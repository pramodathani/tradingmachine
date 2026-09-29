"""Compare the call and the put at one strike on a share.

The program takes the soonest RELIANCE option expiry after today and the strike closest to the share's price, builds the call and the put there, and prints what each premium is made of and where each breaks even.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity_option/put_call_pair.py
"""

import datetime

from tradingmachine.assets import equities


class SharePutCallPair:
    """The call and the put at the same strike and expiry on one share.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the options are written on.
    """

    def __init__(self, underlying_symbol: str = "RELIANCE"):
        """Looks the share up in UBI.

        Args:
            underlying_symbol: The str nse symbol of the share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI has no nse share with that symbol.
        """
        self.share = equities.Equity(exchange="nse", symbol=underlying_symbol)

    def expiry_and_strike(self) -> tuple[datetime.date, float]:
        """Chooses the soonest expiry after today and the strike nearest the share's price.

        Returns:
            A tuple (expiry_date, strike_price), where expiry_date is a datetime.date and strike_price a float in rupees.

        Raises:
            ValueError: No options are listed on the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiries = equities.EquityOption.expiries(
            exchange="nse",
            underlying_symbol=self.share.symbol,
        )
        if not expiries:
            raise ValueError(f"No options are listed on {self.share.symbol}")
        expiry_date = expiries[0]
        today = datetime.date.today()
        for expiry in expiries:
            if expiry > today:
                expiry_date = expiry
                break
        strikes = equities.EquityOption.strikes(
            exchange="nse",
            underlying_symbol=self.share.symbol,
            expiry_date=expiry_date,
        )
        share_price = self.share.last_price
        strike_price = strikes[0]
        for strike in strikes:
            if abs(strike - share_price) < abs(strike_price - share_price):
                strike_price = strike
        return expiry_date, strike_price

    def run(self) -> None:
        """Builds both options and prints them side by side.

        Returns:
            None.

        Raises:
            ValueError: No options are listed on the share.
            tradingmachine.assets.exceptions.EquityOptionError: UBI has no such option.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date, strike_price = self.expiry_and_strike()
        print(f"{self.share.symbol} at {self.share.last_price}")
        print(f"Strike {strike_price}, expiring {expiry_date}")
        option_types = [
            "CE",
            "PE",
        ]
        for option_type in option_types:
            option = equities.EquityOption(
                exchange="nse",
                underlying_symbol=self.share.symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                underlying=self.share,
            )
            print(
                f"{option_type}: premium {option.last_price}, "
                f"intrinsic {option.intrinsic_value:.2f}, "
                f"time value {option.time_value:.2f}, "
                f"in the money {option.in_the_money}, "
                f"breakeven {option.breakeven_price}"
            )


if __name__ == "__main__":
    SharePutCallPair().run()
