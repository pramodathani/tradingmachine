"""Show why a bond future's basis cannot be worked out, and handle it cleanly.

The program builds the soonest future on the 6.33 per cent government security of 2035. It asks for the future's basis twice: first without an underlying, which raises UnderlyingError because a rate future has no default underlying, and then with the security given as the underlying, which raises ServiceUnavailableError because no broker quotes a cash bond. Both errors are caught and explained, and the future's own price is printed.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income_futures/underlying_error_handled.py
"""

from tradingmachine.assets import exceptions
from tradingmachine.assets import fixed_income
from tradingmachine.unified_broker_interface import exceptions as broker_exceptions


class RateFuturesUnderlyingCheck:
    """A check of what a rate future can and cannot say about its underlying.

    Attributes:
        underlying_symbol: The str rate code of the security the future is written on, such as `633GS2035`.
    """

    def __init__(self, underlying_symbol: str = "633GS2035"):
        """Stores the security whose future to check.

        Args:
            underlying_symbol: The str rate code of the security.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Builds the future and asks for its basis with and without an underlying.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.FixedIncomeFuturesError: UBI has no such contract.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiries = fixed_income.FixedIncomeFutures.expiries(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        if not expiries:
            print(f"No futures are listed on {self.underlying_symbol}.")
            return
        contract = fixed_income.FixedIncomeFutures(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiries[0],
        )
        print(f"{self.underlying_symbol} future expiring {contract.expiry_date}")
        print(f"Last price: {contract.last_price}")
        try:
            print(f"Basis: {contract.basis}")
        except exceptions.UnderlyingError as error:
            print(f"Without an underlying: {error}")
        security = fixed_income.FixedIncome(
            exchange="nse",
            symbol=self.underlying_symbol,
        )
        given = fixed_income.FixedIncomeFutures(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiries[0],
            underlying=security,
        )
        try:
            print(f"Basis: {given.basis}")
        except broker_exceptions.ServiceUnavailableError as error:
            print(f"With the security as underlying: {error}")


if __name__ == "__main__":
    RateFuturesUnderlyingCheck().run()
