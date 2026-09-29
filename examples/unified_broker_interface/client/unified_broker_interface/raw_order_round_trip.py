"""Place, change and cancel an order with the client's raw POST, PUT and DELETE calls.

The program reads Vodafone Idea's last price with a GET request, asks UBI's order engine with a POST request to hold a buy limit order for one share about 3% below it, lowers the price by five paise with a PUT request, and cancels the held order with a DELETE request. The cancellation runs whatever happens after the order is placed, so nothing is left behind.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/client/unified_broker_interface/raw_order_round_trip.py
"""

from tradingmachine.unified_broker_interface import client


class RawOrderRoundTrip:
    """One held limit order placed, changed and cancelled through raw REST calls.

    Attributes:
        unified_broker_interface: The tradingmachine.unified_broker_interface.client.UnifiedBrokerInterface the requests are sent through.
    """

    def __init__(self):
        """Creates the client, which reads its api key and secret from MongoDB.

        Raises:
            ValueError: The base url or the MongoDB settings are not configured.
        """
        self.unified_broker_interface = client.UnifiedBrokerInterface()

    def last_price(self) -> dict:
        """Reads Vodafone Idea's last price and instrument id.

        Returns:
            The dict UBI answers from `GET /api/instruments/ltp`, holding `instrument_id` and `last_price`.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.unified_broker_interface.get(
            "/api/instruments/ltp",
            params={
                "exchange": "nse",
                "segment": "equities",
                "symbol": "IDEA",
            },
        )

    def place(self, instrument_id: str, price: float) -> dict:
        """Asks the order engine to hold a buy limit order for one share.

        Args:
            instrument_id: The str UBI instrument id of the share.
            price: The float limit price in rupees.

        Returns:
            The dict UBI answers, holding `outcome`, `parent_id` and `intent_id`.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the order or could not be reached.
        """
        return self.unified_broker_interface.post(
            "/api/orders/place",
            body={
                "instrument_id": instrument_id,
                "transaction_type": "buy",
                "order_type": "limit",
                "product": "mis",
                "quantity": 1,
                "price": price,
                "after_market": False,
                "dry_run": False,
            },
        )

    def run(self) -> None:
        """Places the order, changes its price, and cancels it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        quote = self.last_price()
        price = round(quote["last_price"] * 0.97, 2)
        print(f"IDEA last price {quote['last_price']}, buying at {price}")
        placed = self.place(quote["instrument_id"], price)
        parent_id = placed["parent_id"]
        print(f"POST:   outcome {placed['outcome']}, parent {parent_id}")
        try:
            changed = self.unified_broker_interface.put(
                "/api/orders/modify",
                body={
                    "parent_id": parent_id,
                    "price": round(price - 0.05, 2),
                },
            )
            print(f"PUT:    outcome {changed['outcome']}, new price {changed['price']}")
        finally:
            cancelled = self.unified_broker_interface.delete(
                "/api/orders/parents",
                body={
                    "parent_id": parent_id,
                },
            )
            print(f"DELETE: the parent is now {cancelled['state']}")


if __name__ == "__main__":
    RawOrderRoundTrip().run()
