"""Send several requests UBI refuses and tabulate the error class chosen for each status code.

The client turns each failed response into the subclass of UnifiedBrokerInterfaceError that matches its HTTP status code. The program sends a request with a missing parameter, one for an instrument that does not exist, one with a method the route does not allow and one to an address nothing listens on, catches the base class each time, and prints a small table.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/unified_broker_interface_error/tabulate_failures_by_status_code.py
"""

from collections.abc import Callable

from tradingmachine.unified_broker_interface import client
from tradingmachine.unified_broker_interface import exceptions


class FailureTable:
    """A table of the errors several refused requests raise.

    Attributes:
        unified_broker_interface: The client.UnifiedBrokerInterface for the configured UBI.
        unreachable_client: A client.UnifiedBrokerInterface pointed at a port nothing listens on.
        rows: The list of (str description, str class name, int or None status code) tuples collected.
    """

    def __init__(self):
        """Creates the table with its two clients.

        Raises:
            ValueError: The clients' base url or MongoDB credentials are not configured.
        """
        self.unified_broker_interface = client.UnifiedBrokerInterface()
        self.unreachable_client = client.UnifiedBrokerInterface(
            base_url="http://127.0.0.1:9",
            timeout_seconds=2,
        )
        self.rows = []

    def missing_parameter(self) -> None:
        """Asks for instrument details without naming an instrument.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: Always, as BadRequestError.
        """
        self.unified_broker_interface.get("/api/instruments/details")

    def unknown_instrument(self) -> None:
        """Asks for the details of a share that does not exist.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: Always, as NotFoundError.
        """
        self.unified_broker_interface.get(
            "/api/instruments/details",
            params={
                "exchange": "nse",
                "segment": "equities",
                "symbol": "NOSUCHSHARE",
            },
        )

    def wrong_method(self) -> None:
        """Sends DELETE to a route that only answers GET.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: Always, as ServerError.
        """
        self.unified_broker_interface.delete("/api/instruments/details")

    def nothing_listening(self) -> None:
        """Asks for the session status at an address nothing listens on.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: Always, as UnreachableError.
        """
        self.unreachable_client.status()

    def record(self, description: str, request: Callable[[], None]) -> None:
        """Sends one request and records the error it raises.

        Args:
            description: The str description of the request, for the table.
            request: The callable that sends the request.

        Returns:
            None.

        Raises:
            Nothing.
        """
        try:
            request()
        except exceptions.UnifiedBrokerInterfaceError as error:
            self.rows.append((description, type(error).__name__, error.status_code))
            return
        self.rows.append((description, "no error", None))

    def run(self) -> None:
        """Sends the four requests and prints the table.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.record("missing parameter", self.missing_parameter)
        self.record("unknown instrument", self.unknown_instrument)
        self.record("wrong method", self.wrong_method)
        self.record("nothing listening", self.nothing_listening)
        print(f"{'Request':<20} {'Error class':<24} Status")
        for description, class_name, status_code in self.rows:
            print(f"{description:<20} {class_name:<24} {status_code}")


if __name__ == "__main__":
    FailureTable().run()
