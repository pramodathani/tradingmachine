"""Read the IDEA positions with handling for the BrokerError UBI raises when no broker's data can be read.

When UBI cannot read a single broker's positions it answers HTTP 502 and the client raises BrokerError. A program that reports positions should then say the figures are unavailable rather than report no position. The program reads the net positions in IDEA, handles a BrokerError if there is one, and prints what it found. Nothing is placed.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/broker_error/read_positions_when_no_broker_answers.py
"""

from tradingmachine.assets import equities
from tradingmachine.unified_broker_interface import exceptions


class PositionReport:
    """A report of the IDEA positions that tells unavailable figures apart from none.

    Attributes:
        share: The tradingmachine.assets.equities.Equity reported on.
    """

    def __init__(self):
        """Creates the report for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def run(self) -> None:
        """Reads the positions and prints them, or says they are unavailable.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI failed for a reason other than every broker failing.
        """
        try:
            positions = self.share.net_positions
        except exceptions.BrokerError as error:
            print(f"BrokerError ({error.status_code}): {error.message}")
            print(
                "No broker's positions could be read, so the figures are unavailable rather than zero."
            )
            return
        if positions is None:
            print("Every broker answered, and none holds an IDEA position.")
            return
        print(positions.to_string(index=False))


if __name__ == "__main__":
    PositionReport().run()
