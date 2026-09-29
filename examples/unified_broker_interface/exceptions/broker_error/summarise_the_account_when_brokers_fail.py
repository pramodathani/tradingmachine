"""Summarise positions and holdings for IDEA, catching UnifiedBrokerInterfaceError for each part separately.

A summary built from several reads should still show the parts that worked when one fails. The program reads the IDEA positions and holding, catching the base class UnifiedBrokerInterfaceError around each, so a BrokerError (HTTP 502, no broker's data could be read) or a ServiceUnavailableError (HTTP 503, UBI's document is stale) in one part is reported by status code while the other part is still shown. Nothing is placed.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/broker_error/summarise_the_account_when_brokers_fail.py
"""

from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class IdeaSummary:
    """A summary of what the account has in IDEA, part by part.

    Attributes:
        share: The tradingmachine.assets.equities.Equity summarised.
    """

    def __init__(self):
        """Creates the summary for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def describe_positions(self) -> str:
        """Reads the net positions and describes them.

        Returns:
            A str line with the number of positions, or why they could not be read.

        Raises:
            Nothing.
        """
        try:
            positions = self.share.net_positions
        except exceptions.UnifiedBrokerInterfaceError as error:
            return (
                f"Positions unavailable: {type(error).__name__} ({error.status_code})"
            )
        if positions is None:
            return "Positions: none"
        return f"Positions: {len(positions)} row(s)"

    def describe_holding(self) -> str:
        """Reads the holding and describes it.

        Returns:
            A str line with the quantity held, or why it could not be read.

        Raises:
            Nothing.
        """
        try:
            holding = self.share.holdings
        except exceptions.UnifiedBrokerInterfaceError as error:
            return f"Holding unavailable: {type(error).__name__} ({error.status_code})"
        if holding is None:
            return "Holding: none"
        return f"Holding: {holding['quantity']} shares"

    def run(self) -> None:
        """Prints both parts of the summary.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(self.describe_positions())
        print(self.describe_holding())


if __name__ == "__main__":
    IdeaSummary().run()
