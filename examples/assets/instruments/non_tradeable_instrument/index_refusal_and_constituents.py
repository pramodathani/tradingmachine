"""Show what separates an index from a tradeable instrument, and read its stored constituents.

The program builds the Nifty 50 as a NonTradeableInstrument, shows that asking for it as a TradeableInstrument is refused because an index cannot be traded, and then reads the basket of the index's members stored in MongoDB, if one has been saved.

Typical usage example:

  .venv/bin/python examples/assets/instruments/non_tradeable_instrument/index_refusal_and_constituents.py
"""

from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class IndexRefusalAndConstituents:
    """A short tour of one index as a NonTradeableInstrument.

    Attributes:
        symbol: The str symbol of the index.
        index: The tradingmachine.assets.instruments.NonTradeableInstrument for the index.
    """

    def __init__(self, symbol: str = "NIFTY"):
        """Looks the index up in UBI.

        Args:
            symbol: The str symbol of an NSE equity index.

        Raises:
            tradingmachine.assets.exceptions.NonTradeableInstrumentError: The symbol names something that is not an index.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        self.symbol = symbol
        self.index = instruments.NonTradeableInstrument(
            exchange="nse",
            segment="equity_indices",
            symbol=symbol,
        )

    def show_refusal(self) -> None:
        """Tries to build the index as a TradeableInstrument and prints the refusal.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached.
        """
        try:
            instruments.TradeableInstrument(instrument_id=self.index.instrument_id)
        except exceptions.TradeableInstrumentError as error:
            print("Refused as tradeable:", error)

    def show_constituents(self) -> None:
        """Prints the stored basket of the index's members, or says that none is stored.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: UBI could not find a stored member.
            pymongo.errors.PyMongoError: MongoDB could not be reached.
        """
        basket = self.index.constituents
        if basket is None:
            print(f"No constituents of {self.symbol} are stored for today.")
            return
        print(f"{basket.size} members stored, day change {basket.day_change_percent}")
        print(basket.top_gainers(count=3))

    def run(self) -> None:
        """Prints the index, the refusal and the constituents.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
            pymongo.errors.PyMongoError: MongoDB could not be reached.
        """
        print(self.index, "at", self.index.last_price)
        self.show_refusal()
        self.show_constituents()


if __name__ == "__main__":
    IndexRefusalAndConstituents().run()
