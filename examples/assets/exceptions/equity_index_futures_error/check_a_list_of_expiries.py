"""Check a list of expiry dates and report every one with no contract.

The program looks up a NIFTY futures contract for each date in a list, one listed and the others not. It catches InstrumentError, the base class of every instrument error, so one handler covers EquityIndexFuturesError and anything else the lookup raises about the contract, and it prints the chain of errors behind each date that was not found.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/equity_index_futures_error/check_a_list_of_expiries.py
"""

import datetime

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions


class ExpiryListCheck:
    """A check of several expiry dates of one underlying against UBI.

    Attributes:
        exchange: The str exchange the contracts trade on.
        underlying_symbol: The str symbol the contracts are written on.
        expiry_dates: The list of datetime.date to check, with the first listed expiry added when there is one.
    """

    def __init__(self):
        """Creates the check with the dates to look up.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.underlying_symbol = "NIFTY"
        self.expiry_dates = [
            datetime.date(2026, 12, 25),
            datetime.date(2030, 1, 31),
        ]

    def describe_error_chain(self, error: Exception) -> str:
        """Names an error and every error it was raised from.

        Args:
            error: The Exception to describe.

        Returns:
            A str such as `EquityIndexFuturesError <- InstrumentError <- NotFoundError`.

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

    def check_expiry(self, expiry_date: datetime.date) -> str:
        """Looks one contract up and describes the outcome.

        Args:
            expiry_date: The datetime.date to look a contract up for.

        Returns:
            A str line saying whether UBI knows the contract, and why not when it does not.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup for a reason other than an unknown contract.
        """
        try:
            contract = equities.EquityIndexFutures(
                exchange=self.exchange,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
            )
        except exceptions.InstrumentError as error:
            chain = self.describe_error_chain(error)
            return f"{expiry_date}: not found ({chain})"
        return f"{expiry_date}: found, lot size {contract.lot_size}"

    def run(self) -> None:
        """Adds the first listed expiry to the dates, checks each one and prints a line for it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        listed_expiries = equities.EquityIndexFutures.expiries(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
        )
        if listed_expiries:
            self.expiry_dates.insert(0, listed_expiries[0])
        else:
            print(
                f"No {self.underlying_symbol} contract is listed, which is expected for a mistyped name."
            )
        for expiry_date in self.expiry_dates:
            print(self.check_expiry(expiry_date))


if __name__ == "__main__":
    ExpiryListCheck().run()
