"""Look up the order engine's stored answer to an order by its intent id.

The program asks UBI's order engine to hold a buy limit order for one Vodafone Idea share about 3% below the last price, which does not fill, reads the engine's stored answer to that placement back through `Account.intent`, and cancels the held order before it ends, whatever happens.

Typical usage example:

  .venv/bin/python examples/accounts/account/account/order_intent_lookup.py
"""

from tradingmachine.accounts import account
from tradingmachine.assets import equities


class OrderIntentLookup:
    """A placement whose outcome is read back from the engine by its intent id.

    Attributes:
        trading_account: The tradingmachine.accounts.account.Account the intent is read through.
        idea: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE, which the order is placed in.
    """

    def __init__(self):
        """Creates the account and looks the share up in UBI.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
        """
        self.trading_account = account.Account()
        self.idea = equities.Equity(exchange="nse", symbol="IDEA")

    def limit_price(self) -> float:
        """Works out a buy price about 3% below the last price, on the tick.

        Returns:
            The float limit price in rupees, rounded to the 0.01 tick.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not give the last price.
        """
        return round(self.idea.last_price * 0.97, 2)

    def run(self) -> None:
        """Places the held order, prints the engine's stored answer, and cancels the order.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        price = self.limit_price()
        answer = self.idea.buy_at_limit_price(price=price, quantity=1, product="mis")
        print(f"Placed: outcome {answer['outcome']}, parent {answer['parent_id']}")
        try:
            engine_answer = self.trading_account.intent(answer["intent_id"])
            response = engine_answer["response"]
            print(f"Intent {engine_answer['intent_id']}")
            print(f"Stored HTTP status: {engine_answer['status']}")
            print(f"Stored outcome: {response['outcome']}")
            print(f"Stored parent id: {response['parent_id']}")
        finally:
            cancelled = self.idea.cancel_parent(answer["parent_id"])
            print(f"Cancelled: the parent is now {cancelled['state']}")


if __name__ == "__main__":
    OrderIntentLookup().run()
