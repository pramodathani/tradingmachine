"""Send a limit order outside the day's price band and detect its rejection, whether it comes at once or later.

A broker can refuse an order as it is sent, which UBI reports as OrderRejectedError with HTTP 422, or accept it and have its risk checks or the exchange reject it a moment later, which shows only as a `REJECTED` status in the order book. The program sends a buy limit order for one IDEA share at half the last price straight to the broker, far below the day's lower price band, catches the base class UnifiedBrokerInterfaceError and recognises an outright rejection by its status code 422, and otherwise waits for the order's status. The order can never fill at that price, and if it is still open after the wait it is cancelled.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/order_rejected_error/detect_a_rejection_now_or_later.py
"""

import decimal
import time

from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class PriceBandRejection:
    """A limit order far outside the price band, followed until it is rejected.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the order is for.
        wait_seconds: The int number of seconds to wait for the order's final status.
        finished_statuses: The list of str statuses after which an order can no longer change.
    """

    def __init__(self):
        """Creates the order's setting for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.wait_seconds = 20
        self.finished_statuses = [
            "REJECTED",
            "CANCELLED",
            "COMPLETE",
        ]

    def half_price(self) -> float:
        """Works out half the last price, rounded down to the tick.

        Returns:
            The float limit price in rupees.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not give the last price.
        """
        target = decimal.Decimal(str(self.share.last_price)) / 2
        ticks = (target / self.share.tick_size).to_integral_value(
            rounding=decimal.ROUND_FLOOR
        )
        return float(ticks * self.share.tick_size)

    def order_row(self, order_id: str) -> dict | None:
        """Finds the order in today's orders for the share.

        Args:
            order_id: The str broker order id.

        Returns:
            The dict row of the order, or None when the order book does not show it yet.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the orders.
        """
        orders = self.share.orders
        if orders is None:
            return None
        for row in orders.to_dict("records"):
            if row["order_id"] == order_id:
                return row
        return None

    def wait_for_final_status(self, order_id: str) -> dict | None:
        """Reads the order's row once a second until its status is final.

        Args:
            order_id: The str broker order id.

        Returns:
            The dict row with a final status, or the last row seen, or None when the order never appeared.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the orders.
        """
        row = None
        for attempt in range(self.wait_seconds):
            row = self.order_row(order_id)
            if row is not None and row["status"] in self.finished_statuses:
                return row
            time.sleep(1)
        return row

    def run(self) -> None:
        """Sends the order, reports how it was rejected, and cancels it if it is still open.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order for a reason other than a rejection, or refused the cancel.
        """
        price = self.half_price()
        try:
            answer = self.share.buy_at_limit_price(
                price=price,
                quantity=1,
                product="cnc",
                hold=False,
            )
        except exceptions.UnifiedBrokerInterfaceError as error:
            if error.status_code != 422:
                raise
            print(f"Rejected at once with {type(error).__name__}: {error.message}")
            return
        order_id = answer["order_id"]
        print(f"Buy at {price} accepted by {answer['broker']} as {order_id}")
        row = self.wait_for_final_status(order_id)
        if row is not None and row["status"] == "REJECTED":
            print(f"Rejected afterwards: {row['status_message']}")
            return
        print(
            f"Not rejected; status {None if row is None else row['status']}, so cancelling it."
        )
        cancel_answer = self.share.cancel_order(
            order_id=order_id, broker=answer["broker"]
        )
        print(f"Cancelled: {cancel_answer}")


if __name__ == "__main__":
    PriceBandRejection().run()
