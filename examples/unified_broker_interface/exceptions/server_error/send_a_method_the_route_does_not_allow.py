"""Send a DELETE to a route that only answers GET and handle the ServerError.

HTTP 405 has no more specific class in the client, so it arrives as ServerError, the class for any failure status without its own subclass. The program sends DELETE to the instrument details route, catches ServerError, and prints the status code.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/server_error/send_a_method_the_route_does_not_allow.py
"""

from tradingmachine.unified_broker_interface import client
from tradingmachine.unified_broker_interface import exceptions


class WrongMethodRequest:
    """A request sent with a method the route does not allow.

    Attributes:
        unified_broker_interface: The client.UnifiedBrokerInterface the request is sent through.
        path: The str route the request is sent to.
    """

    def __init__(self):
        """Creates the request with its client and route.

        Raises:
            ValueError: The client's base url or MongoDB credentials are not configured.
        """
        self.unified_broker_interface = client.UnifiedBrokerInterface()
        self.path = "/api/instruments/details"

    def run(self) -> None:
        """Sends the request and prints the error.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI failed with a status that has its own subclass.
        """
        try:
            answer = self.unified_broker_interface.delete(self.path)
        except exceptions.ServerError as error:
            print(f"ServerError ({error.status_code}): {error.message}")
            return
        print(f"Unexpectedly answered: {answer}")


if __name__ == "__main__":
    WrongMethodRequest().run()
