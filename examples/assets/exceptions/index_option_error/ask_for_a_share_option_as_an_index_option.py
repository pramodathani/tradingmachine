"""Ask for a RELIANCE option through the IndexOption class and handle the IndexOptionError.

IndexOption accepts only an option on an index. The program looks a RELIANCE share option up through it, catches IndexOptionError, and builds the same option through the general Option class instead.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/index_option_error/ask_for_a_share_option_as_an_index_option.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class ShareOptionAsIndexOption:
    """A lookup of a share option through the IndexOption class.

    Attributes:
        exchange: The str exchange the option trades on.
        segment: The str UBI segment of share options.
        underlying_symbol: The str symbol of the share.
    """

    def __init__(self):
        """Creates the lookup for a RELIANCE option.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.segment = "equity_options"
        self.underlying_symbol = "RELIANCE"

    def run(self) -> None:
        """Looks the option up as an index option, catches the error and builds it as a plain option.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know the option.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date = equities.EquityOption.expiries(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
        )[-1]
        strike_prices = equities.EquityOption.strikes(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )
        strike_price = strike_prices[len(strike_prices) // 2]
        try:
            option = instruments.IndexOption(
                exchange=self.exchange,
                segment=self.segment,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type="PE",
            )
        except exceptions.IndexOptionError as error:
            print(f"IndexOptionError: {error}")
            option = instruments.Option(
                exchange=self.exchange,
                segment=self.segment,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type="PE",
            )
        print(f"Built {option!r}")
        print(f"Lot size: {option.lot_size}")


if __name__ == "__main__":
    ShareOptionAsIndexOption().run()
