"""Place an order with handling for the OrderRejectedError UBI raises when a broker refuses it outright.

When a broker refuses an order as it is sent, UBI answers HTTP 422 and the client raises OrderRejectedError, whose detail holds the order document with the broker's reason. The program places a buy limit order for one IDEA share about 3% below the last price, which UBI's order engine holds rather than sends, prints the broker's reason if the order is refused, and cancels the held order at once.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/order_rejected_error/read_the_brokers_reason_for_a_rejection.py
"""

import decimal

from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class RejectionAwareOrder:
    """A held limit order whose outright rejection is explained from the order document.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the order is for.
    """

    def __init__(self):
        """Creates the order's setting for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

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
        """Places the order, explains a rejection, and cancels an accepted order.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order for a reason other than a broker rejection, or refused the cancel.
        """
        try:
            answer = self.share.buy_at_limit_price(
                price=self.limit_price(),
                quantity=1,
                product="cnc",
            )
        except exceptions.OrderRejectedError as error:
            print(f"OrderRejectedError: {error.message}")
            print(f"Broker: {error.detail.get('broker')}")
            print(f"Broker's reason: {error.detail.get('status_message')}")
            return
        parent_id = answer["parent_id"]
        try:
            print(f"Not rejected: outcome {answer['outcome']}, parent {parent_id}")
        finally:
            cancel_answer = self.share.cancel_parent(parent_id)
            print(f"Cancelled: {cancel_answer['state']}")


if __name__ == "__main__":
    RejectionAwareOrder().run()
