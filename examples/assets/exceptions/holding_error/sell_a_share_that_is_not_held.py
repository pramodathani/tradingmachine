"""Try to sell shares that are not held and handle the HoldingError.

The program reads the account's holding of Vodafone Idea first and stops if any is held, so it never sells a real holding. When none is held, `reduce_holdings` finds nothing to sell and raises HoldingError before any order is sent.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/holding_error/sell_a_share_that_is_not_held.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions


class UnheldShareSale:
    """An attempt to sell one share of a stock the account does not hold.

    Attributes:
        share: The tradingmachine.assets.equities.Equity to sell.
    """

    def __init__(self):
        """Creates the attempt for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def run(self) -> None:
        """Checks that nothing is held, then asks to sell and prints the refusal.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        holding = self.share.holdings
        if holding is not None:
            print(
                f"{holding['quantity']} IDEA shares are held, so this program does not try to sell any."
            )
            return
        try:
            answer = self.share.reduce_holdings(quantity=1, price=100.0)
        except exceptions.HoldingError as error:
            print(f"HoldingError: {error}")
            return
        print(f"Unexpectedly sent: {answer}")


if __name__ == "__main__":
    UnheldShareSale().run()
