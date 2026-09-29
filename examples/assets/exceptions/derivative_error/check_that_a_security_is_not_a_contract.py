"""Ask for a share as a derivative and handle the DerivativeError.

A Derivative must be a future or an option with an expiry date. The program looks the IDEA share up through the Derivative class, catches DerivativeError, and prints the message, which names the shape UBI gave the instrument.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/derivative_error/check_that_a_security_is_not_a_contract.py
"""

from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class SecurityAsDerivative:
    """A lookup of a share through the Derivative class.

    Attributes:
        exchange: The str exchange of the share.
        segment: The str UBI segment of the share.
        symbol: The str symbol of the share.
    """

    def __init__(self):
        """Creates the lookup for the IDEA share.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.segment = "equities"
        self.symbol = "IDEA"

    def run(self) -> None:
        """Looks the share up as a derivative and prints why it is refused.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        try:
            contract = instruments.Derivative(
                exchange=self.exchange,
                segment=self.segment,
                symbol=self.symbol,
            )
        except exceptions.DerivativeError as error:
            print(f"DerivativeError: {error}")
            return
        print(f"Unexpectedly a contract: {contract!r}, expiring {contract.expiry_date}")


if __name__ == "__main__":
    SecurityAsDerivative().run()
