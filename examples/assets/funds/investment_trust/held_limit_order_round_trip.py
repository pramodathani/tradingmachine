"""Place a held limit order for one EMBASSY unit and cancel it straight away.

The program bids for one unit of the trust, for delivery, at a limit 3 per cent below the last price, rounded to the tick. UBI's order engine holds such an order rather than sending it, and answers with a `parent_id`. The program lists the trust's open parents to show the order is there, then cancels it, whatever happens in between, and confirms it is gone.

Typical usage example:

  .venv/bin/python examples/assets/funds/investment_trust/held_limit_order_round_trip.py
"""

from tradingmachine.assets import funds


class HeldLimitOrderRoundTrip:
    """One held limit order placed and cancelled on an investment trust.

    Attributes:
        trust: The funds.InvestmentTrust the order is placed on.
        discount: The float fraction below the last price the bid is placed at.
    """

    def __init__(self):
        """Looks EMBASSY up in UBI.

        Raises:
            tradingmachine.assets.exceptions.InvestmentTrustError: UBI has no such trust.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        self.trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
        self.discount = 0.03

    def run(self) -> None:
        """Places the bid, lists the open parents, cancels the bid and lists them again.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        last_price = self.trust.last_price
        tick_size = float(self.trust.tick_size)
        ticks = round(last_price * (1 - self.discount) / tick_size)
        limit_price = round(ticks * tick_size, 2)
        print(f"Last price {last_price}, bidding {limit_price} for one unit")
        answer = self.trust.buy_at_limit_price(
            price=limit_price,
            quantity=1,
            product="cnc",
            tag="exampletrust",
        )
        parent_id = answer["parent_id"]
        print(f"Outcome: {answer['outcome']}, parent: {parent_id}")
        try:
            self._print_parents("Open parents after placing")
        finally:
            cancelled = self.trust.cancel_parent(parent_id)
            print(f"Cancelled: state {cancelled['state']}")
        self._print_parents("Open parents after cancelling")

    def _print_parents(self, heading: str) -> None:
        """Prints the trust's open parents under a heading.

        Args:
            heading: The str line to print first.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print(heading)
        parents = self.trust.parents
        if parents is None:
            print("  none")
            return
        print(parents[["parent_order_id", "synthetic_type", "state"]])


if __name__ == "__main__":
    HeldLimitOrderRoundTrip().run()
