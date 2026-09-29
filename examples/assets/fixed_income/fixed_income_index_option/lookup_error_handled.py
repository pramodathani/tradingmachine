"""Try to build an option on a fixed income index and handle the error UBI gives today.

No broker maps anything into UBI's fixed income index options segment, so every lookup fails. The program asks for an overnight MIBOR call at the expiry of the soonest MIBOR future, catches the FixedIncomeIndexOptionError that is raised, and prints it, so the same code will simply start working the day UBI carries these options.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income_index_option/lookup_error_handled.py
"""

from tradingmachine.assets import exceptions
from tradingmachine.assets import fixed_income


class RateIndexOptionLookup:
    """An attempt to build one option on a fixed income index.

    Attributes:
        underlying_symbol: The str symbol of the index, such as `ONMIBOR`.
    """

    def __init__(self, underlying_symbol: str = "ONMIBOR"):
        """Stores the index to look an option up on.

        Args:
            underlying_symbol: The str symbol of the index.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Tries to build the option and prints either the option or the error.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        futures_expiries = fixed_income.FixedIncomeIndexFutures.expiries(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        if not futures_expiries:
            print(f"No futures are listed on {self.underlying_symbol} either.")
            return
        expiry_date = futures_expiries[0]
        try:
            option = fixed_income.FixedIncomeIndexOption(
                exchange="nse",
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
                strike_price=95,
                option_type="CE",
            )
        except exceptions.FixedIncomeIndexOptionError as error:
            print(f"Not available today: {error}")
            return
        print(f"Found {option.underlying_symbol} {option.strike_price} CE")
        print(f"Premium: {option.last_price}")


if __name__ == "__main__":
    RateIndexOptionLookup().run()
