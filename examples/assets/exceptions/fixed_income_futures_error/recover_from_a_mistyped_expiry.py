"""Recover from a mistyped expiry date by catching FixedIncomeFuturesError.

The program asks for an interest rate future on the 6.33% 2035 government bond on a day no contract expires, catches FixedIncomeFuturesError, then reads the expiries that are listed and builds the contract for the first one on or after the day asked for.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/fixed_income_futures_error/recover_from_a_mistyped_expiry.py
"""

import datetime

from tradingmachine.assets import fixed_income
from tradingmachine.assets import exceptions


class MistypedExpiryRecovery:
    """A lookup of a futures contract that falls back to a listed expiry.

    Attributes:
        exchange: The str exchange the contract trades on.
        underlying_symbol: The str symbol the contract is written on.
        wanted_expiry_date: The datetime.date the person asked for, on which no contract expires.
    """

    def __init__(self):
        """Creates the lookup with the contract the person asked for.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.underlying_symbol = "633GS2035"
        self.wanted_expiry_date = datetime.date(2026, 12, 25)

    def build_contract(
        self, expiry_date: datetime.date
    ) -> fixed_income.FixedIncomeFutures:
        """Looks one contract up in UBI.

        Args:
            expiry_date: The datetime.date the contract expires on.

        Returns:
            The fixed_income.FixedIncomeFutures UBI knows for that expiry.

        Raises:
            tradingmachine.assets.exceptions.FixedIncomeFuturesError: UBI has no such contract.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        return fixed_income.FixedIncomeFutures(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )

    def listed_expiry_on_or_after(self) -> datetime.date | None:
        """Picks the listed expiry closest after the day asked for.

        Returns:
            The first listed datetime.date on or after wanted_expiry_date, or the last listed one when every expiry is earlier, or None when nothing is listed.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        listed_expiries = fixed_income.FixedIncomeFutures.expiries(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
        )
        for expiry_date in listed_expiries:
            if expiry_date >= self.wanted_expiry_date:
                return expiry_date
        if listed_expiries:
            return listed_expiries[-1]
        return None

    def run(self) -> None:
        """Asks for the mistyped contract, recovers from the error and prints the contract found.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        try:
            contract = self.build_contract(self.wanted_expiry_date)
        except exceptions.FixedIncomeFuturesError as error:
            print(f"FixedIncomeFuturesError: {error}")
            listed_expiry = self.listed_expiry_on_or_after()
            if listed_expiry is None:
                print(
                    f"No {self.underlying_symbol} contract is listed on the {self.exchange}, which is expected for a mistyped name."
                )
                return
            print(f"Using the listed expiry {listed_expiry} instead.")
            contract = self.build_contract(listed_expiry)
        print(f"Contract: {contract!r}")
        print(f"Expires on {contract.expiry_date}, in {contract.days_to_expiry} days")
        print(f"Lot size: {contract.lot_size}")


if __name__ == "__main__":
    MistypedExpiryRecovery().run()
