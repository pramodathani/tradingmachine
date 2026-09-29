"""Follow a held limit order from placement through a price change to its cancellation.

UBI's order engine holds a plain day limit order instead of sending it to a broker, and sends it only once the other side of the book reaches its price. The program bids for one Vodafone Idea share 3 per cent below the market, finds the order among the engine's parents, lowers its price to 4 per cent below, reads it back, and cancels it, checking at the end that nothing is left open. The order is far enough from the market that it is never sent.

Typical usage example:

  .venv/bin/python examples/assets/instruments/tradeable_instrument/held_limit_order_lifecycle.py
"""

from tradingmachine.assets import equities


class HeldLimitOrderLifecycle:
    """One held limit order, followed from start to finish.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the order is placed in.
        parent_id: The str id the engine gave the held order, or None before it is placed.
    """

    def __init__(self):
        """Looks Vodafone Idea up in UBI.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.parent_id = None

    def place(self) -> None:
        """Bids for one share 3 per cent below the last price and keeps the parent id.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or could not be reached.
        """
        price = round(self.share.last_price * 0.97, 2)
        answer = self.share.buy_at_limit_price(price=price, quantity=1, product="cnc")
        self.parent_id = answer["parent_id"]
        print(f"Placed at {price}: {answer['outcome']}, parent {self.parent_id}")

    def show(self) -> None:
        """Prints the held order as the engine keeps it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the parent.
        """
        parent = self.share.parent(self.parent_id)
        print(f"  state {parent['state']}, type {parent['synthetic_type']}")
        print(f"  body {parent['body']}")

    def lower_price(self) -> None:
        """Moves the held order's price to 4 per cent below the last price.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the change.
        """
        new_price = round(self.share.last_price * 0.96, 2)
        changed = self.share.modify_order(parent_id=self.parent_id, price=new_price)
        print(f"Lowered to {new_price}: {changed['outcome']}")

    def cancel(self) -> None:
        """Cancels the held order and checks that no parent of this program is still open.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the cancel.
        """
        cancelled = self.share.cancel_parent(self.parent_id)
        print(f"Cancelled: {cancelled['state']}")
        parents = self.share.parents
        still_open = False
        if parents is not None:
            still_open = self.parent_id in list(parents["parent_order_id"])
        print(f"Still open: {still_open}")

    def run(self) -> None:
        """Places, shows, changes and cancels the order, cancelling it even when a step fails.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        self.place()
        try:
            self.show()
            self.lower_price()
            self.show()
        finally:
            self.cancel()


if __name__ == "__main__":
    HeldLimitOrderLifecycle().run()
