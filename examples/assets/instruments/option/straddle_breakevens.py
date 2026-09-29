"""Price an at-the-money straddle on Reliance and print where it breaks even.

A straddle is one call and one put at the same strike, bought together, which pays off when the share moves far in either direction. The program builds both options at the strike nearest the share price on the nearest expiry, and prints the cost of one lot of each, the intrinsic and time value in each premium, the notional value controlled and the two share prices at which the straddle breaks even at expiry.

Typical usage example:

  .venv/bin/python examples/assets/instruments/option/straddle_breakevens.py
"""

import datetime

from tradingmachine.assets import equities


class StraddleBreakevens:
    """An at-the-money straddle on one share.

    Attributes:
        underlying_symbol: The str symbol of the share.
        share: The tradingmachine.assets.equities.Equity the options are written on.
    """

    def __init__(self, underlying_symbol: str = "RELIANCE"):
        """Looks the share up in UBI.

        Args:
            underlying_symbol: The str symbol of an NSE share with options.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.underlying_symbol = underlying_symbol
        self.share = equities.Equity(exchange="nse", symbol=underlying_symbol)

    def build_leg(
        self,
        expiry_date: datetime.date,
        strike: float,
        option_type: str,
    ) -> equities.EquityOption:
        """Builds one option of the straddle.

        Args:
            expiry_date: The datetime.date of the expiry.
            strike: The float strike price.
            option_type: The str option type, `CE` or `PE`.

        Returns:
            The tradingmachine.assets.equities.EquityOption.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        return equities.EquityOption(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
            strike_price=strike,
            option_type=option_type,
            underlying=self.share,
        )

    def run(self) -> None:
        """Prints the straddle's legs, its total cost and its breakevens.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        expiries = equities.EquityOption.expiries(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        expiry_date = expiries[0]
        strikes = equities.EquityOption.strikes(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )
        share_price = self.share.last_price
        strike = strikes[0]
        for candidate in strikes:
            if abs(candidate - share_price) < abs(strike - share_price):
                strike = candidate
        call = self.build_leg(expiry_date, strike, "CE")
        put = self.build_leg(expiry_date, strike, "PE")
        print(
            f"{self.underlying_symbol} at {share_price}, strike {strike}, {expiry_date}"
        )
        total_premium = 0.0
        for option in [
            call,
            put,
        ]:
            premium = option.last_price
            total_premium = total_premium + premium
            print(
                f"  {option.option_type}: premium {premium}, intrinsic "
                f"{option.intrinsic_value:.2f}, time {option.time_value:.2f}, "
                f"in the money {option.in_the_money}, one lot Rs {option.premium_per_lot:,.0f}"
            )
        print(f"  notional per lot Rs {call.notional_value:,.0f}")
        print(f"  straddle costs {total_premium:.2f} a share")
        print(
            f"  breaks even below {strike - total_premium:.2f} or above {strike + total_premium:.2f}"
        )
        print(
            f"  call breakeven {call.breakeven_price:.2f}, put breakeven {put.breakeven_price:.2f}"
        )


if __name__ == "__main__":
    StraddleBreakevens().run()
