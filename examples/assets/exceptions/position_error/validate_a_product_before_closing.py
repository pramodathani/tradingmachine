"""Check which products `liquidate_position` accepts, catching InstrumentError.

The program asks `liquidate_position` to close an IDEA position under each of `cover`, `margin_trading` and `bracket`, three products UBI reports positions under but cannot send orders for. Each is refused with PositionError before anything is read or sent, which one handler for the base class InstrumentError catches, so no order is placed whatever the account holds.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/position_error/validate_a_product_before_closing.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions


class ProductValidation:
    """A check that the products UBI cannot send orders under are refused.

    Attributes:
        share: The tradingmachine.assets.equities.Equity whose position is named.
        products: The list of str products to try.
    """

    def __init__(self):
        """Creates the check for the IDEA share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.products = [
            "cover",
            "margin_trading",
            "bracket",
        ]

    def run(self) -> None:
        """Tries every product and prints the refusal for each.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        for product in self.products:
            try:
                answer = self.share.liquidate_position(product=product)
            except exceptions.InstrumentError as error:
                print(f"{product}: refused with {type(error).__name__}")
                continue
            print(f"{product}: unexpectedly sent {answer}")


if __name__ == "__main__":
    ProductValidation().run()
