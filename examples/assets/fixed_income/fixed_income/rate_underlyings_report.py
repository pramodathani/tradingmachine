"""List the government securities that interest rate futures are written on.

The program searches the nse's fixed income segment for rate codes such as `633GS2035`, which name the interest rate underlyings, and prints how many futures and option expiries are listed on each.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income/rate_underlyings_report.py
"""

from tradingmachine.assets import fixed_income


class RateUnderlyingsReport:
    """The interest rate underlyings on the nse and the derivatives written on them.

    Attributes:
        term: The str the rate codes must contain, such as `GS2035`.
    """

    def __init__(self, term: str = "GS2035"):
        """Stores the part of the rate code to search for.

        Args:
            term: The str the rate codes must contain, such as `GS2035` for securities maturing in 2035.

        Raises:
            Nothing.
        """
        self.term = term

    def run(self) -> None:
        """Finds the underlyings and prints the derivatives listed on each.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.FixedIncomeError: An underlying found could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        matches = fixed_income.FixedIncome.search(exchange="nse", term=self.term)
        if matches is None:
            print(f"No rate code contains {self.term}.")
            return
        for rate_code in matches["symbol"]:
            security = fixed_income.FixedIncome(exchange="nse", symbol=rate_code)
            futures_expiries = fixed_income.FixedIncomeFutures.expiries(
                exchange="nse",
                underlying_symbol=security.symbol,
            )
            option_expiries = fixed_income.FixedIncomeOption.expiries(
                exchange="nse",
                underlying_symbol=security.symbol,
            )
            print(
                f"{security.symbol}: {len(futures_expiries)} futures expiries, "
                f"{len(option_expiries)} option expiries"
            )


if __name__ == "__main__":
    RateUnderlyingsReport().run()
