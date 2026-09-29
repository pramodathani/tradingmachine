"""Try a list of UBI addresses in turn, catching UnifiedBrokerInterfaceError until one answers.

A program might be given an old address for UBI. The program tries a port nothing listens on first, catches the UnreachableError through the base class UnifiedBrokerInterfaceError, recognises it by its missing status code, and falls back to the address configured in `TRADINGMACHINE_UBI_BASE_URL`, printing the session status from the first address that answers.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/unreachable_error/fall_back_to_the_configured_address.py
"""

from tradingmachine.unified_broker_interface import client
from tradingmachine.unified_broker_interface import exceptions


class AddressFallback:
    """A connection that tries several addresses for UBI.

    Attributes:
        base_urls: The list of str addresses to try, where None means the configured one.
    """

    def __init__(self):
        """Creates the connection with the addresses to try.

        Raises:
            Nothing.
        """
        self.base_urls = [
            "http://127.0.0.1:9",
            None,
        ]

    def first_answer(self) -> dict | None:
        """Asks each address for the session status until one answers.

        Returns:
            The dict session status from the first address that answers, or None when none does.

        Raises:
            ValueError: The configured address or the MongoDB credentials are not set.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: An address answered with a failure rather than not answering at all.
        """
        for base_url in self.base_urls:
            unified_broker_interface = client.UnifiedBrokerInterface(
                base_url=base_url,
                timeout_seconds=5,
            )
            try:
                return unified_broker_interface.status()
            except exceptions.UnifiedBrokerInterfaceError as error:
                if error.status_code is not None:
                    raise
                print(f"{base_url} did not answer: {type(error).__name__}")
        return None

    def run(self) -> None:
        """Finds an address that answers and prints the session status.

        Returns:
            None.

        Raises:
            ValueError: The configured address or the MongoDB credentials are not set.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: An address answered with a failure.
        """
        status = self.first_answer()
        if status is None:
            print("No address answered.")
            return
        print(f"Session status: {status}")


if __name__ == "__main__":
    AddressFallback().run()
