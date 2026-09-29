"""Try to redeem a mutual fund scheme that is not held, catching InstrumentError.

The program reads the account's holding of one mutual fund scheme first and stops if any is held, so it never redeems a real holding. When none is held, `liquidate_holdings` finds nothing to sell and raises HoldingError before any order is sent, which one handler for the base class InstrumentError catches.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/holding_error/redeem_a_fund_that_is_not_held.py
"""

from tradingmachine.assets import exceptions
from tradingmachine.assets import mutual_funds


class UnheldFundRedemption:
    """An attempt to redeem every unit of a scheme the account does not hold.

    Attributes:
        scheme: The tradingmachine.assets.mutual_funds.MutualFund to redeem.
    """

    def __init__(self):
        """Creates the attempt for one Aditya Birla Sun Life scheme.

        Raises:
            tradingmachine.assets.exceptions.MutualFundError: UBI does not know the scheme.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.scheme = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")

    def run(self) -> None:
        """Checks that nothing is held, then asks to redeem and prints the refusal.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        holding = self.scheme.holdings
        if holding is not None:
            print(
                f"{holding['quantity']} units are held, so this program does not redeem any."
            )
            return
        try:
            answer = self.scheme.liquidate_holdings(price=10.0)
        except exceptions.InstrumentError as error:
            print(f"{type(error).__name__}: {error}")
            return
        print(f"Unexpectedly sent: {answer}")


if __name__ == "__main__":
    UnheldFundRedemption().run()
