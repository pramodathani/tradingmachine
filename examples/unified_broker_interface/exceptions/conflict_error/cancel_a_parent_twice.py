"""Cancel a held order twice and handle the ConflictError the second cancel raises.

The program places a buy limit order for one IDEA share about 3% below the last price, which UBI's order engine holds rather than sends, and cancels it at once. It then cancels it again, which UBI refuses with HTTP 409 because the parent is already cancelled, and prints the ConflictError. If anything goes wrong before the first cancel, the order is still cancelled on the way out.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/conflict_error/cancel_a_parent_twice.py
"""

import decimal

from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class DoubleCancel:
    """A held limit order that is cancelled twice.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the order is for.
        parent_id: The str parent id of the held order, or None before it is placed.
        cancelled: A bool that is True once the first cancel went through.
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

    def limit_price(self) -> float:
        """Works out a buy price about 3% below the last price, rounded down to the tick.

        Returns:
            The float limit price in rupees.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not give the last price.
        """
        target = decimal.Decimal(str(self.share.last_price)) * decimal.Decimal("0.97")
        ticks = (target / self.share.tick_size).to_integral_value(
            rounding=decimal.ROUND_FLOOR
        )
        return float(ticks * self.share.tick_size)

    def run(self) -> None:
        """Places the held order, cancels it twice and prints the second answer.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or the first cancel.
        """
        price = self.limit_price()
        answer = self.share.buy_at_limit_price(
            price=price,
            quantity=1,
            product="cnc",
        )
        self.parent_id = answer["parent_id"]
        print(
            f"Held buy at {price}: parent {self.parent_id}, outcome {answer['outcome']}"
        )
        try:
            first_answer = self.share.cancel_parent(self.parent_id)
            self.cancelled = True
            print(f"First cancel: {first_answer['state']}")
            try:
                self.share.cancel_parent(self.parent_id)
            except exceptions.ConflictError as error:
                print(
                    f"Second cancel: ConflictError ({error.status_code}): {error.message}"
                )
                return
            print("Second cancel: unexpectedly accepted")
        finally:
            if not self.cancelled:
                self.share.cancel_parent(self.parent_id)


if __name__ == "__main__":
    DoubleCancel().run()
