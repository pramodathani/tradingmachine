"""Check a list of strike prices and report every one with no option.

The program looks up a NIFTY call option at several strike prices for the soonest expiry, one listed and the others not. It catches InstrumentError, the base class of every instrument error, so one handler covers EquityIndexOptionError and anything else the lookup raises about the option, and it prints the chain of errors behind each strike that was not found.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/equity_index_option_error/check_a_list_of_strikes.py
"""

import datetime

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions


class StrikeListCheck:
    """A check of several strike prices of one expiry against UBI.

    Attributes:
        exchange: The str exchange the options trade on.
        underlying_symbol: The str symbol the options are written on.
        fallback_expiry_date: The datetime.date to ask for when no expiry is listed at all.
        strike_prices: The list of float strikes to check, with a listed strike added when there is one.
    """

    def __init__(self):
        """Creates the check with the strikes to look up.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.underlying_symbol = "NIFTY"
        self.fallback_expiry_date = datetime.date(2026, 10, 6)
        self.strike_prices = [
            25010.0,
            1.0,
        ]

    def describe_error_chain(self, error: Exception) -> str:
        """Names an error and every error it was raised from.

        Args:
            error: The Exception to describe.

        Returns:
            A str such as `EquityIndexOptionError <- InstrumentError <- NotFoundError`.

        Raises:
            Nothing.
        """
        names = [
            type(error).__name__,
        ]
        cause = error.__cause__
        while cause is not None:
            names.append(type(cause).__name__)
            cause = cause.__cause__
        return " <- ".join(names)

    def check_strike(self, expiry_date: datetime.date, strike_price: float) -> str:
        """Looks one call option up and describes the outcome.

        Args:
            expiry_date: The datetime.date the option expires on.
            strike_price: The float strike price to look up.

        Returns:
            A str line saying whether UBI knows the option, and why not when it does not.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup for a reason other than an unknown option.
        """
        try:
            option = equities.EquityIndexOption(
                exchange=self.exchange,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type="CE",
            )
        except exceptions.InstrumentError as error:
            chain = self.describe_error_chain(error)
            return f"{strike_price}: not found ({chain})"
        return f"{strike_price}: found, lot size {option.lot_size}"

    def run(self) -> None:
        """Picks the soonest expiry, adds a listed strike, checks each strike and prints a line for it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        listed_expiries = equities.EquityIndexOption.expiries(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
        )
        expiry_date = self.fallback_expiry_date
        if listed_expiries:
            expiry_date = listed_expiries[0]
        listed_strikes = equities.EquityIndexOption.strikes(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )
        if listed_strikes:
            middle_strike = listed_strikes[len(listed_strikes) // 2]
            self.strike_prices.insert(0, middle_strike)
        else:
            print(
                f"No strike is listed for {expiry_date}, which is expected for a mistyped name."
            )
        print(f"Checking {self.underlying_symbol} calls expiring {expiry_date}:")
        for strike_price in self.strike_prices:
            print(self.check_strike(expiry_date, strike_price))


if __name__ == "__main__":
    StrikeListCheck().run()
