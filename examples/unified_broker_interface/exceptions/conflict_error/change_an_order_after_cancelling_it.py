"""Change the price of a held order after it was cancelled, catching UnifiedBrokerInterfaceError.

A program that changes orders can race with a cancel from elsewhere. The program places a buy limit order for one IDEA share about 3% below the last price, which UBI's order engine holds, cancels it, and then asks to lower its price. UBI refuses with HTTP 409, and the program catches the ConflictError through the base class UnifiedBrokerInterfaceError and recognises it by its status code. If anything goes wrong before the cancel, the order is still cancelled on the way out.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/conflict_error/change_an_order_after_cancelling_it.py
"""

import decimal

from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class LateModification:
    """A held limit order whose price is changed after it was cancelled.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the order is for.
        parent_id: The str parent id of the held order, or None before it is placed.
        cancelled: A bool that is True once the cancel went through.
    """

    def __init__(self):
        """Creates the order's setting for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.parent_id = None
        self.cancelled = False

    def limit_price(self) -> decimal.Decimal:
        """Works out a buy price about 3% below the last price, rounded down to the tick.

        Returns:
            The decimal.Decimal limit price in rupees.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not give the last price.
        """
        target = decimal.Decimal(str(self.share.last_price)) * decimal.Decimal("0.97")
        ticks = (target / self.share.tick_size).to_integral_value(
            rounding=decimal.ROUND_FLOOR
        )
        return ticks * self.share.tick_size

    def run(self) -> None:
        """Places the held order, cancels it, then tries to change it and prints the refusal.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or the cancel.
        """
        price = self.limit_price()
        answer = self.share.buy_at_limit_price(
            price=float(price),
            quantity=1,
            product="cnc",
        )
        self.parent_id = answer["parent_id"]
        print(f"Held buy at {price}: parent {self.parent_id}")
        try:
            self.share.cancel_parent(self.parent_id)
            self.cancelled = True
            print("Cancelled the held order.")
            lower_price = price - self.share.tick_size
            try:
                self.share.modify_order(
                    parent_id=self.parent_id, price=float(lower_price)
                )
            except exceptions.UnifiedBrokerInterfaceError as error:
                if error.status_code != 409:
                    raise
                print(f"Change refused with {type(error).__name__}: {error.message}")
                return
            print("Change unexpectedly accepted.")
        finally:
            if not self.cancelled:
                self.share.cancel_parent(self.parent_id)


if __name__ == "__main__":
    LateModification().run()
