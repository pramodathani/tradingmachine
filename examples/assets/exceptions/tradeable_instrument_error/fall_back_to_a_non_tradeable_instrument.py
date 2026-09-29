"""Ask for an index as a tradeable instrument, catch TradeableInstrumentError and read it as an index instead.

An index can be followed but not traded, so building a TradeableInstrument for NIFTY raises TradeableInstrumentError. The program catches it, builds a NonTradeableInstrument for the same index, and prints its last value.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/tradeable_instrument_error/fall_back_to_a_non_tradeable_instrument.py
"""

from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class IndexFallback:
    """A lookup that tries an instrument as tradeable first and as an index second.

    Attributes:
        exchange: The str exchange of the instrument.
        segment: The str UBI segment of the instrument.
        symbol: The str symbol of the instrument.
    """

    def __init__(self):
        """Creates the lookup for the NIFTY index.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.segment = "equity_indices"
        self.symbol = "NIFTY"

    def build(self) -> instruments.Instrument:
        """Builds the instrument as tradeable, or as non-tradeable when it is an index.

        Returns:
            A tradingmachine.assets.instruments.TradeableInstrument, or a tradingmachine.assets.instruments.NonTradeableInstrument when the instrument is an index.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know the instrument.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        try:
            return instruments.TradeableInstrument(
                exchange=self.exchange,
                segment=self.segment,
                symbol=self.symbol,
            )
        except exceptions.TradeableInstrumentError as error:
            print(f"TradeableInstrumentError: {error}")
        return instruments.NonTradeableInstrument(
            exchange=self.exchange,
            segment=self.segment,
            symbol=self.symbol,
        )

    def run(self) -> None:
        """Builds the instrument and prints its class and last value.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know the instrument.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        instrument = self.build()
        print(f"Built {instrument!r}")
        print(f"Last value: {instrument.last_price}")


if __name__ == "__main__":
    IndexFallback().run()
