"""Ask for a RELIANCE future through the Option class and handle the OptionError.

The program reads the soonest RELIANCE futures expiry and looks that contract up through the Option class. UBI finds the contract, but it is a future rather than an option, so the Option class raises OptionError, which the program catches before building the contract as a Futures instead.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/option_error/ask_for_a_future_as_an_option.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class FutureAsOption:
    """A lookup of a RELIANCE future through the Option class.

    Attributes:
        exchange: The str exchange the future trades on.
        segment: The str UBI segment of share futures.
        underlying_symbol: The str symbol of the share.
    """

    def __init__(self):
        """Creates the lookup for a RELIANCE future.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.segment = "equity_futures"
        self.underlying_symbol = "RELIANCE"

    def run(self) -> None:
        """Looks the future up as an option, catches the error and builds it as a future.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know the future.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date = equities.EquityFutures.expiries(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
        )[0]
        try:
            contract = instruments.Option(
                exchange=self.exchange,
                segment=self.segment,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
            )
        except exceptions.OptionError as error:
            print(f"OptionError: {error}")
            contract = instruments.Futures(
                exchange=self.exchange,
                segment=self.segment,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
            )
        print(f"Built {contract!r}")
        print(f"Lot size: {contract.lot_size}")


if __name__ == "__main__":
    FutureAsOption().run()
