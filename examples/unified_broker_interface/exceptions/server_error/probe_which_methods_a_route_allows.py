"""Probe which HTTP methods a route allows, catching UnifiedBrokerInterfaceError.

The program sends GET, POST, PUT, PATCH and DELETE to the session status route, which only answers GET. Each refused method raises ServerError for HTTP 405, which is caught through the base class UnifiedBrokerInterfaceError, and the program prints the status of each method. None of the refused requests changes anything.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/server_error/probe_which_methods_a_route_allows.py
"""

from collections.abc import Callable
from typing import Any

from tradingmachine.unified_broker_interface import client
from tradingmachine.unified_broker_interface import exceptions


class MethodProbe:
    """A probe of the methods one route answers.

    Attributes:
        unified_broker_interface: The client.UnifiedBrokerInterface the requests are sent through.
        path: The str route probed.
    """

    def __init__(self):
        """Creates the probe with its client and route.

        Raises:
            ValueError: The client's base url or MongoDB credentials are not configured.
        """
        self.unified_broker_interface = client.UnifiedBrokerInterface()
        self.path = "/api/session/status"

    def probe(self, method_name: str, send: Callable[[str], Any]) -> None:
        """Sends one method to the route and prints the outcome.

        Args:
            method_name: The str HTTP method, for the printed line.
            send: The client method that sends it, taking the route.

        Returns:
            None.

        Raises:
            Nothing.
        """
        try:
            send(self.path)
        except exceptions.UnifiedBrokerInterfaceError as error:
            print(
                f"{method_name:<7} refused: {type(error).__name__} ({error.status_code})"
            )
            return
        print(f"{method_name:<7} allowed")

    def run(self) -> None:
        """Probes the five methods.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.probe("GET", self.unified_broker_interface.get)
        self.probe("POST", self.unified_broker_interface.post)
        self.probe("PUT", self.unified_broker_interface.put)
        self.probe("PATCH", self.unified_broker_interface.patch)
        self.probe("DELETE", self.unified_broker_interface.delete)


if __name__ == "__main__":
    MethodProbe().run()
