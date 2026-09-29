"""Ask for a NIFTY option through the Futures class and handle the FuturesError.

The program reads the soonest NIFTY option expiry and a strike listed for it, then looks that option up through the Futures class. UBI finds the contract, but it is an option rather than a future, so the Futures class raises FuturesError, which the program catches before building the contract as an Option instead.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/futures_error/ask_for_an_option_as_a_future.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class OptionAsFuture:
    """A lookup of a NIFTY option through the Futures class.

    Attributes:
        exchange: The str exchange the option trades on.
        segment: The str UBI segment of NIFTY options.
        underlying_symbol: The str symbol of the index.
    """

    def __init__(self):
        """Creates the lookup for a NIFTY option.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.segment = "equity_index_options"
        self.underlying_symbol = "NIFTY"

    def run(self) -> None:
        """Looks the option up as a future, catches the error and builds it as an option.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know the option.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date = equities.EquityIndexOption.expiries(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
        )[0]
        strike_prices = equities.EquityIndexOption.strikes(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )
        strike_price = strike_prices[len(strike_prices) // 2]
        try:
            contract = instruments.Futures(
                exchange=self.exchange,
                segment=self.segment,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type="CE",
            )
        except exceptions.FuturesError as error:
            print(f"FuturesError: {error}")
            contract = instruments.Option(
                exchange=self.exchange,
                segment=self.segment,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type="CE",
            )
        print(f"Built {contract!r}")
        print(f"Lot size: {contract.lot_size}")


if __name__ == "__main__":
    OptionAsFuture().run()
