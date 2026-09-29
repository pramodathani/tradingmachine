"""Buy one share intraday, report the position, and close it.

The program buys one Vodafone Idea share under the intraday product with a marketable limit order, which fills at once at the best offer and, unlike a market order, is accepted by every broker's API. It waits for the position to grow by that share, prints the order, the trade, the position's value and its profit or loss, and then sells the share back through reduce_position, which UBI routes to the broker holding the position, so the position ends where it began apart from charges.

Typical usage example:

  .venv/bin/python examples/assets/instruments/tradeable_instrument/intraday_round_trip_report.py
"""

import time

import pandas as pd

from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class IntradayRoundTripReport:
    """One intraday buy and sell of a single share, with a report in between.

    Attributes:
        share: The tradingmachine.assets.equities.Equity that is traded.
        start_quantity: The int intraday quantity held before the program traded.
    """

    def __init__(self):
        """Looks Vodafone Idea up in UBI.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.start_quantity = 0

    def intraday_quantity(self) -> int:
        """Reads the quantity of the share's open intraday position.

        Returns:
            The int quantity, positive when long, negative when short and zero when none is open.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the positions.
        """
        positions = self.share.net_positions
        if positions is None:
            return 0
        intraday = positions[positions["product"] == "intraday"]
        return int(intraday["quantity"].sum())

    def wait_for_quantity(self, wanted: int) -> bool:
        """Waits up to thirty seconds for the intraday position to reach a quantity.

        Args:
            wanted: The int quantity to wait for.

        Returns:
            A bool that is True when the position reached the quantity in time.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the positions.
        """
        for attempt in range(30):
            if self.intraday_quantity() == wanted:
                return True
            time.sleep(1)
        return False

    def report(self, order_id: str) -> None:
        """Prints the buy order, its trade and the position's value and profit.

        Args:
            order_id: The str id of the buy order.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the books.
        """
        orders = self.share.orders
        order = orders[orders["order_id"] == order_id]
        print(order[["order_id", "status", "average_price", "filled_quantity"]])
        trades = self.share.trades
        if trades is None:
            print("The trade book does not show the trade yet.")
        else:
            print(
                trades[trades["order_id"] == order_id][
                    ["trade_id", "quantity", "price"]
                ]
            )
        print("Position value:", self.share.positions_value)
        print("Profit or loss:", self.share.positions_pnl)

    def trade_difference(self, quantity: int) -> None:
        """Sends one order that brings the intraday position from a quantity back to where it started.

        The order is a limit a per cent through the market, which fills at once. When it shrinks the position it is sent through reduce_position, so UBI routes it against the brokers that hold the position rather than leaving one broker long and another short.

        Args:
            quantity: The int intraday quantity held now.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI or the broker refused the order.
        """
        difference = quantity - self.start_quantity
        if difference > 0:
            price = round(self.share.last_price * 0.99, 2)
        else:
            price = round(self.share.last_price * 1.01, 2)
        if (difference > 0) == (quantity > 0):
            self.share.reduce_position(
                quantity=abs(difference),
                product="mis",
                price=price,
            )
        elif difference > 0:
            self.share.sell_at_limit_price(
                price=price,
                quantity=difference,
                product="mis",
                hold=False,
            )
        else:
            self.share.buy_at_limit_price(
                price=price,
                quantity=-difference,
                product="mis",
                hold=False,
            )

    def restore_position(self) -> None:
        """Trades back to the intraday quantity the program started from, trying again when a broker refuses.

        Each attempt waits five seconds for the positions to settle, so an order whose outcome was unknown is counted before another is sent, and then trades the difference through trade_difference.

        Returns:
            None.

        Raises:
            SystemExit: The position could not be brought back after six attempts.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the positions.
        """
        quantity = None
        for attempt in range(6):
            time.sleep(5)
            try:
                quantity = self.intraday_quantity()
                if quantity == self.start_quantity:
                    break
                self.trade_difference(quantity)
            except exceptions.UnifiedBrokerInterfaceError as error:
                quantity = None
                print("Closing failed, trying again:", error)
        if quantity != self.start_quantity:
            raise SystemExit(f"The position is {quantity}, not {self.start_quantity}.")
        print("Intraday quantity back at", quantity)

    def run(self) -> None:
        """Buys, reports and sells back, selling back even when the report fails.

        Returns:
            None.

        Raises:
            SystemExit: The position could not be brought back to where it started.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        pd.set_option("display.width", 120)
        self.start_quantity = self.intraday_quantity()
        bought = None
        try:
            bought = self.share.buy_at_marketable_price(quantity=1, product="mis")
            print("Bought:", bought["outcome"], bought["order_id"])
            if self.wait_for_quantity(self.start_quantity + 1):
                self.report(bought["order_id"])
            else:
                print("The position did not grow within thirty seconds.")
        finally:
            if bought is not None:
                try:
                    self.share.cancel_parent(bought["parent_id"])
                except exceptions.ConflictError:
                    print("The buy had already finished.")
                except exceptions.UnifiedBrokerInterfaceError as error:
                    print("Could not cancel the buy:", error)
            self.restore_position()


if __name__ == "__main__":
    IntradayRoundTripReport().run()
