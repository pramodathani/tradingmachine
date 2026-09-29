"""Check that UBI is reachable, the session is live and every broker's data is fresh.

The program connects to UBI, prints when the access token expires and how long it has left, lists the brokers UBI is connected to, and reports how fresh each broker's funds are, flagging any broker whose data UBI marks as anything other than `ok`.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/client/unified_broker_interface/session_health_check.py
"""

import datetime

from tradingmachine.unified_broker_interface import client


class SessionHealthCheck:
    """A health check of the UBI session and the brokers behind it.

    Attributes:
        unified_broker_interface: The tradingmachine.unified_broker_interface.client.UnifiedBrokerInterface the checks are sent through.
    """

    def __init__(self):
        """Creates the client, which reads its api key and secret from MongoDB.

        Raises:
            ValueError: The base url or the MongoDB settings are not configured.
        """
        self.unified_broker_interface = client.UnifiedBrokerInterface()

    def check_session(self) -> None:
        """Connects and prints the session's state and the token's remaining life.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the api key or could not be reached.
        """
        self.unified_broker_interface.connect()
        session = self.unified_broker_interface.status()
        expires_at = datetime.datetime.fromisoformat(session["expires_at"])
        remaining = expires_at - datetime.datetime.now()
        print(f"Session: {session['status']}")
        print(f"Token expires at {expires_at:%Y-%m-%d %H:%M}, in {remaining}")

    def check_brokers(self) -> None:
        """Prints every connected broker and how fresh its funds are.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        brokers = self.unified_broker_interface.get("/api/brokers/details")
        print(f"Brokers connected: {len(brokers)}")
        funds = self.unified_broker_interface.get("/api/portfolio/funds")
        for broker in funds["brokers"]:
            flag = ""
            if broker["status"] != "ok":
                flag = "  <- check this broker"
            print(
                f"  {broker['broker']:<10} {broker['status']:<6} {broker['as_of']}{flag}"
            )

    def run(self) -> None:
        """Runs both checks.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        self.check_session()
        self.check_brokers()


if __name__ == "__main__":
    SessionHealthCheck().run()
