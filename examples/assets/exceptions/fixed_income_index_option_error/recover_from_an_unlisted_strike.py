"""Recover from a strike price that is not listed by catching FixedIncomeIndexOptionError.

The program asks for an overnight MIBOR call option at a strike price that is not listed, catches FixedIncomeIndexOptionError, then reads the strikes that are listed for the expiry and builds the option at the one nearest the strike asked for.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/fixed_income_index_option_error/recover_from_an_unlisted_strike.py
"""

import datetime

from tradingmachine.assets import fixed_income
from tradingmachine.assets import exceptions


class UnlistedStrikeRecovery:
    """A lookup of an option that falls back to the nearest listed strike.

    Attributes:
        exchange: The str exchange the option trades on.
        underlying_symbol: The str symbol the option is written on.
        fallback_expiry_date: The datetime.date to ask for when no expiry is listed at all.
        wanted_strike_price: The float strike price the person asked for, which is not listed.
        option_type: The str option type, `CE` for a call.
    """

    def __init__(self):
        """Creates the lookup with the option the person asked for.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.underlying_symbol = "ONMIBOR"
        self.fallback_expiry_date = datetime.date(2026, 10, 30)
        self.wanted_strike_price = 100.0
        self.option_type = "CE"

    def nearest_expiry(self) -> datetime.date:
        """Picks the soonest listed expiry.

        Returns:
            The first listed datetime.date, or fallback_expiry_date when nothing is listed.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        listed_expiries = fixed_income.FixedIncomeIndexOption.expiries(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
        )
        if listed_expiries:
            return listed_expiries[0]
        return self.fallback_expiry_date

    def nearest_listed_strike(self, expiry_date: datetime.date) -> float | None:
        """Picks the listed strike closest to the one asked for.

        Args:
            expiry_date: The datetime.date whose strikes to read.

        Returns:
            The float listed strike nearest wanted_strike_price, or None when no strike is listed.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        listed_strikes = fixed_income.FixedIncomeIndexOption.strikes(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )
        nearest_strike = None
        for strike_price in listed_strikes:
            if nearest_strike is None:
                nearest_strike = strike_price
                continue
            distance = abs(strike_price - self.wanted_strike_price)
            if distance < abs(nearest_strike - self.wanted_strike_price):
                nearest_strike = strike_price
        return nearest_strike

    def build_option(
        self,
        expiry_date: datetime.date,
        strike_price: float,
    ) -> fixed_income.FixedIncomeIndexOption:
        """Looks one option up in UBI.

        Args:
            expiry_date: The datetime.date the option expires on.
            strike_price: The float strike price of the option.

        Returns:
            The fixed_income.FixedIncomeIndexOption UBI knows for that expiry and strike.

        Raises:
            tradingmachine.assets.exceptions.FixedIncomeIndexOptionError: UBI has no such option.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        return fixed_income.FixedIncomeIndexOption(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
            strike_price=strike_price,
            option_type=self.option_type,
        )

    def run(self) -> None:
        """Asks for the unlisted strike, recovers from the error and prints the option found.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date = self.nearest_expiry()
        try:
            option = self.build_option(expiry_date, self.wanted_strike_price)
        except exceptions.FixedIncomeIndexOptionError as error:
            print(f"FixedIncomeIndexOptionError: {error}")
            strike_price = self.nearest_listed_strike(expiry_date)
            if strike_price is None:
                print(
                    f"No strike is listed for {expiry_date}, which is expected for a segment no broker fills."
                )
                return
            print(f"Using the listed strike {strike_price} instead.")
            option = self.build_option(expiry_date, strike_price)
        print(f"Option: {option!r}")
        print(
            f"Strike {option.strike_price} {option.option_type}, expiring {option.expiry_date}"
        )
        print(f"Lot size: {option.lot_size}")


if __name__ == "__main__":
    UnlistedStrikeRecovery().run()
