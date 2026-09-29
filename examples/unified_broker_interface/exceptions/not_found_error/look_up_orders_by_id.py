"""Look several ids up in UBI, catching UnifiedBrokerInterfaceError for the ones it does not know.

The program asks UBI about a broker order id, an order engine parent id and an intent id, all of which are made up, as a program reconciling its own records against UBI might. Each lookup raises NotFoundError, which is caught through the base class UnifiedBrokerInterfaceError and reported with its status code. Nothing is placed, and cancelling an order that does not exist changes nothing.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/not_found_error/look_up_orders_by_id.py
"""

from collections.abc import Callable

from tradingmachine.accounts import account
from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class OrderIdReconciliation:
    """A reconciliation of made-up order ids against UBI.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the order lookups are sent through.
        trading_account: The tradingmachine.accounts.account.Account the intent lookup is sent through.
    """

    def __init__(self):
        """Creates the reconciliation for the IDEA share and the account.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.trading_account = account.Account()

    def cancel_unknown_order(self) -> dict:
        """Cancels a broker order id that no broker holds.

        Returns:
            The dict UBI answers with, which it never does for this id.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: Always, as NotFoundError.
        """
        return self.share.cancel_order(order_id="999999999999999")

    def read_unknown_parent(self) -> dict:
        """Reads a parent id the order engine does not hold.

        Returns:
            The dict UBI answers with, which it never does for this id.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: Always, as NotFoundError.
        """
        return self.share.parent("00000000-0000-0000-0000-000000000000")

    def read_unknown_intent(self) -> dict:
        """Reads an intent id the order engine never answered.

        Returns:
            The dict UBI answers with, which it never does for this id.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: Always, as NotFoundError.
        """
        return self.trading_account.intent("00000000000000000000000000000000")

    def check(self, label: str, lookup: Callable[[], dict]) -> None:
        """Runs one lookup and prints what UBI said.

        Args:
            label: The str description of the lookup.
            lookup: The callable that sends the lookup.

        Returns:
            None.

        Raises:
            Nothing.
        """
        try:
            answer = lookup()
        except exceptions.UnifiedBrokerInterfaceError as error:
            print(
                f"{label}: {type(error).__name__} ({error.status_code}): {error.message}"
            )
            return
        print(f"{label}: found {answer}")

    def run(self) -> None:
        """Runs the three lookups.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.check("broker order", self.cancel_unknown_order)
        self.check("engine parent", self.read_unknown_parent)
        self.check("engine intent", self.read_unknown_intent)


if __name__ == "__main__":
    OrderIdReconciliation().run()
