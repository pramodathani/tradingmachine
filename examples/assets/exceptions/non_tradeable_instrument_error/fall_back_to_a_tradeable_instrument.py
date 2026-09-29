"""Ask for a share as a non-tradeable instrument, catch NonTradeableInstrumentError and read it as tradeable instead.

Only an index is a NonTradeableInstrument, so building one for the IDEA share raises NonTradeableInstrumentError. The program catches it, builds a TradeableInstrument for the same share, and prints its best bid and offer from the order book, which only a tradeable instrument has.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/non_tradeable_instrument_error/fall_back_to_a_tradeable_instrument.py
"""

from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class TradeableFallback:
    """A lookup that tries an instrument as an index first and as tradeable second.

    Attributes:
        exchange: The str exchange of the instrument.
        segment: The str UBI segment of the instrument.
        symbol: The str symbol of the instrument.
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
        """Builds the instrument, recovers from the error and prints its best prices.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know the instrument.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        try:
            index = instruments.NonTradeableInstrument(
                exchange=self.exchange,
                segment=self.segment,
                symbol=self.symbol,
            )
        except exceptions.NonTradeableInstrumentError as error:
            print(f"NonTradeableInstrumentError: {error}")
        else:
            print(f"{index!r} is an index, with last value {index.last_price}")
            return
        share = instruments.TradeableInstrument(
            exchange=self.exchange,
            segment=self.segment,
            symbol=self.symbol,
        )
        print(f"Built {share!r} instead")
        print(f"Best bid: {share.best_bid}")
        print(f"Best offer: {share.best_offer}")


if __name__ == "__main__":
    TradeableFallback().run()
