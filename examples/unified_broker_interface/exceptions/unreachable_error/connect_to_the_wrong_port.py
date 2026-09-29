"""Connect to an address where UBI is not running and handle the UnreachableError.

When no response arrives at all, such as when UBI is stopped or the address is wrong, the client raises UnreachableError, whose status code is None. The program points a client at a port nothing listens on, asks for the session status, catches UnreachableError and prints it.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/unreachable_error/connect_to_the_wrong_port.py
"""

from tradingmachine.unified_broker_interface import client
from tradingmachine.unified_broker_interface import exceptions


class WrongPortConnection:
    """A connection attempt to a port where UBI does not listen.

    Attributes:
        unified_broker_interface: The client.UnifiedBrokerInterface pointed at the wrong port.
    """

    def __init__(self):
        """Creates the client with the wrong address and a short timeout.

        Raises:
            ValueError: The MongoDB credentials are not configured.
        """
        self.unified_broker_interface = client.UnifiedBrokerInterface(
            base_url="http://127.0.0.1:9",
            timeout_seconds=2,
        )

    def run(self) -> None:
        """Asks for the session status and prints the error.

        Returns:
            None.

        Raises:
            Nothing.
        """
        try:
            status = self.unified_broker_interface.status()
        except exceptions.UnreachableError as error:
            print(f"UnreachableError, status code {error.status_code}")
            print(error.message)
            return
        print(f"Unexpectedly connected: {status}")


if __name__ == "__main__":
    WrongPortConnection().run()
