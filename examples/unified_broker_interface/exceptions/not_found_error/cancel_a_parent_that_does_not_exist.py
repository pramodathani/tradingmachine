"""Cancel an order engine parent that does not exist and handle the NotFoundError.

A parent id that was mistyped, or that belongs to a parent the engine has long forgotten, is unknown to UBI's order engine. The program asks to cancel such a parent on the IDEA share, catches NotFoundError, and prints UBI's explanation. Nothing is placed or cancelled.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/not_found_error/cancel_a_parent_that_does_not_exist.py
"""

from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class UnknownParentCancel:
    """A cancel request for a parent the order engine does not hold.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the cancel is sent through.
        parent_id: The str parent id, which no parent has.
    """

    def __init__(self):
        """Creates the request for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.parent_id = "00000000-0000-0000-0000-000000000000"

    def run(self) -> None:
        """Sends the cancel and prints why it was refused.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI failed for a reason other than an unknown parent.
        """
        try:
            answer = self.share.cancel_parent(self.parent_id)
        except exceptions.NotFoundError as error:
            print(f"NotFoundError ({error.status_code}): {error.message}")
            return
        print(f"Unexpectedly cancelled: {answer}")


if __name__ == "__main__":
    UnknownParentCancel().run()
