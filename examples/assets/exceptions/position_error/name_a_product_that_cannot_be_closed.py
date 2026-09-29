"""Ask to reduce a position under a product UBI cannot close and handle the PositionError.

UBI sends orders only under the cnc, mis and nrml products, so a position under a bracket order cannot be reduced through it. The program asks `reduce_position` to reduce an IDEA position under `bracket`, which is refused with PositionError before anything is read or sent, so no order is placed whatever the account holds.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/position_error/name_a_product_that_cannot_be_closed.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions


class BracketPositionReduction:
    """An attempt to reduce a position held under a bracket order.

    Attributes:
        share: The tradingmachine.assets.equities.Equity whose position to reduce.
        product: The str product named, which UBI cannot send orders under.
    """

    def __init__(self):
        """Creates the attempt for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.product = "bracket"

    def run(self) -> None:
        """Asks for the reduction and prints why it is refused.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        try:
            answer = self.share.reduce_position(quantity=1, product=self.product)
        except exceptions.PositionError as error:
            print(f"PositionError: {error}")
            print("Close such a position at the broker, or name cnc, mis or nrml.")
            return
        print(f"Unexpectedly sent: {answer}")


if __name__ == "__main__":
    BracketPositionReduction().run()
