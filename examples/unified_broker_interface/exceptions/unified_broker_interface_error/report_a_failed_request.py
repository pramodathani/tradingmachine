"""Send a request UBI refuses and report the UnifiedBrokerInterfaceError it raises.

Every failure the client reports is a UnifiedBrokerInterfaceError, which carries the message, the HTTP status code and the body UBI answered with. The program asks UBI for the details of a share that does not exist, catches the base class, and prints all three.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/unified_broker_interface_error/report_a_failed_request.py
"""

from tradingmachine.unified_broker_interface import client
from tradingmachine.unified_broker_interface import exceptions


class FailedRequestReport:
    """A report of one request UBI refuses.

    Attributes:
        unified_broker_interface: The client.UnifiedBrokerInterface the request is sent through.
        parameters: The dict of query parameters naming a share that does not exist.
    """

    def __init__(self):
        """Creates the report with its client and the request to send.

        Raises:
            ValueError: The client's base url or MongoDB credentials are not configured.
        """
        self.unified_broker_interface = client.UnifiedBrokerInterface()
        self.parameters = {
            "exchange": "nse",
            "segment": "equities",
            "symbol": "NOSUCHSHARE",
        }

    def run(self) -> None:
        """Sends the request and prints what the error carries.

        Returns:
            None.

        Raises:
            Nothing.
        """
        try:
            details = self.unified_broker_interface.get(
                "/api/instruments/details",
                params=self.parameters,
            )
        except exceptions.UnifiedBrokerInterfaceError as error:
            print(f"Class: {type(error).__name__}")
            print(f"Message: {error.message}")
            print(f"HTTP status code: {error.status_code}")
            print(f"Body: {error.detail}")
            return
        print(f"Unexpectedly found: {details}")


if __name__ == "__main__":
    FailedRequestReport().run()
