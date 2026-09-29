"""Place a held limit order for one NIFTYBEES unit and cancel it straight away.

The program bids for one unit, for delivery, at a limit 3 per cent below the last price, rounded to the tick. UBI's order engine holds such an order rather than sending it, and answers with a `parent_id`. The program then shows the held order among the fund's parents and cancels it, whatever happens in between, so nothing is left behind.

Typical usage example:

  .venv/bin/python examples/assets/funds/exchange_traded_fund/held_limit_order_round_trip.py
"""

from tradingmachine.assets import funds


class HeldLimitOrderRoundTrip:
    """One held limit order placed and cancelled on an exchange traded fund.

    Attributes:
        fund: The funds.ExchangeTradedFund the order is placed on.
        discount: The float fraction below the last price the bid is placed at.
    """

    def __init__(self):
        """Looks NIFTYBEES up in UBI.

        Raises:
            tradingmachine.assets.exceptions.ExchangeTradedFundError: UBI has no such fund.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        self.fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
        self.discount = 0.03

    def run(self) -> None:
        """Places the bid, shows the held order, and cancels it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        last_price = self.fund.last_price
        limit_price = self._round_to_tick(last_price * (1 - self.discount))
        print(f"Last price {last_price}, bidding {limit_price} for one unit")
        answer = self.fund.buy_at_limit_price(
            price=limit_price,
            quantity=1,
            product="cnc",
            tag="exampleetf",
        )
        print(f"Outcome: {answer['outcome']}, parent: {answer.get('parent_id')}")
        try:
            self._show_parent(answer["parent_id"])
        finally:
            cancelled = self.fund.cancel_parent(answer["parent_id"])
            print(f"Cancelled: state {cancelled['state']}")

    def _show_parent(self, parent_id: str) -> None:
        """Prints the held order as the order engine keeps it.

        Args:
            parent_id: The str id of the held order.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        parent = self.fund.parent(parent_id)
        print(f"Held order {parent['parent_order_id']}")
        print(f"  type {parent['synthetic_type']}, state {parent['state']}")
        print(f"  body {parent['body']}")

    def _round_to_tick(self, price: float) -> float:
        """Rounds a price to the nearest multiple of the fund's tick size.

        Args:
            price: The float price to round.

        Returns:
            The float price on the tick grid.

        Raises:
            Nothing.
        """
        tick_size = float(self.fund.tick_size)
        ticks = round(price / tick_size)
        return round(ticks * tick_size, 2)


if __name__ == "__main__":
    HeldLimitOrderRoundTrip().run()
