"""Ask UBI for instrument details without naming an instrument and handle the BadRequestError.

The details route needs an instrument id, or an exchange, a segment and the fields that identify one instrument. The program sends only an exchange and a segment, catches BadRequestError, and prints UBI's explanation of what was missing.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/bad_request_error/ask_for_details_without_an_instrument.py
"""

from tradingmachine.unified_broker_interface import client
from tradingmachine.unified_broker_interface import exceptions


class IncompleteDetailsRequest:
    """A details request that leaves out the symbol.

    Attributes:
        unified_broker_interface: The client.UnifiedBrokerInterface the request is sent through.
        parameters: The dict of incomplete query parameters.
    """

    def __init__(self):
        """Creates the request with its client and parameters.

        Raises:
            ValueError: The client's base url or MongoDB credentials are not configured.
        """
        self.unified_broker_interface = client.UnifiedBrokerInterface()
        self.parameters = {
            "exchange": "nse",
            "segment": "equities",
        }

    def run(self) -> None:
        """Sends the request and prints why it was refused.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI failed for a reason other than a malformed request.
        """
        try:
            details = self.unified_broker_interface.get(
                "/api/instruments/details",
                params=self.parameters,
            )
        except exceptions.BadRequestError as error:
            print(f"BadRequestError ({error.status_code}): {error.message}")
            return
        print(f"Unexpectedly found: {details}")


if __name__ == "__main__":
    IncompleteDetailsRequest().run()
