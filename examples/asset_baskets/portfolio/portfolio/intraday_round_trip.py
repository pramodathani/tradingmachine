"""Buy one Vodafone Idea share intraday through a portfolio and sell it straight back.

The program builds a portfolio of one IDEA share, sends it to the market with `place_orders` as an intraday market order, waits for the order book to show the order's final status, and, once it has filled, sells the share again with the same call in the opposite direction. An order still open after the wait is cancelled instead, so the program leaves nothing behind. It places real orders and should be run while the market is open.

Typical usage example:

  .venv/bin/python examples/asset_baskets/portfolio/portfolio/intraday_round_trip.py
"""

import time

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import portfolio
from tradingmachine.assets import equities

FINAL_STATUSES = [
    "COMPLETE",
    "REJECTED",
    "CANCELLED",
]

OPEN_STATUSES = [
    "OPEN",
    "PENDING",
]

WAIT_ATTEMPTS = 15

WAIT_SECONDS = 2


class IntradayRoundTrip:
    """One IDEA share bought and sold again through a one-member portfolio.

    Attributes:
        idea: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        one_share: The tradingmachine.asset_baskets.portfolio.Portfolio holding one IDEA share.
    """

    def __init__(self):
        """Looks the share up in UBI and builds the portfolio.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
        """
        self.idea = equities.Equity(exchange="nse", symbol="IDEA")
        self.one_share = portfolio.Portfolio(
            name="one IDEA share",
            members=[
                basket_member.BasketMember(self.idea, quantity=1),
            ],
        )

    def wait_for_status(self, order_id: str) -> str | None:
        """Reads the order book until the order reaches a final status or the wait ends.

        Args:
            order_id: The str broker order id to look for.

        Returns:
            The str last status seen, such as `COMPLETE`, or None when the order never appeared.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the order book.
        """
        status = None
        for attempt in range(WAIT_ATTEMPTS):
            time.sleep(WAIT_SECONDS)
            orders = self.idea.orders
            if orders is None:
                continue
            matching = orders[orders["order_id"].astype(str) == order_id]
            if matching.empty:
                continue
            status = matching["status"].iloc[0]
            if status in FINAL_STATUSES:
                break
        return status

    def sell_back(self) -> None:
        """Sells the share again through the portfolio, falling back to reducing the position.

        UBI chooses a broker for every order on its own, so the sale may go to a broker that does not hold the share, and some brokers refuse that. When the sale is not accepted, the position is reduced by one share instead, which UBI sends in the direction and at the size the position needs.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        sold = self.one_share.place_orders(
            product="mis", transaction_type="sell", tag="roundtrip"
        )
        print(sold[["label", "transaction_type", "status", "outcome", "error"]])
        if sold.loc[0, "outcome"] != "accepted":
            closed = self.idea.reduce_position(
                quantity=1, product="mis", tag="roundtrip"
            )
            print(
                f"The sale was refused, so the position was reduced: {closed['outcome']}"
            )
            return
        sell_status = self.wait_for_status(str(sold.loc[0, "order_id"]))
        print(f"The sell order is {sell_status}")

    def run(self) -> None:
        """Buys the share, waits for the fill, and sells it back or cancels the buy.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        bought = self.one_share.place_orders(product="mis", tag="roundtrip")
        print(bought[["label", "transaction_type", "status", "outcome", "order_id"]])
        if bought.loc[0, "outcome"] != "accepted":
            print(f"The buy was not accepted: {bought.loc[0, 'error']}")
            return
        order_id = str(bought.loc[0, "order_id"])
        status = self.wait_for_status(order_id)
        print(f"The buy order is {status}")
        if status == "COMPLETE":
            self.sell_back()
        elif status in OPEN_STATUSES or status is None:
            cancelled = self.idea.cancel_order(order_id)
            print(f"Cancelled the buy: {cancelled['outcome']}")


if __name__ == "__main__":
    IntradayRoundTrip().run()
