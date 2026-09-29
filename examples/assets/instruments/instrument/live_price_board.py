"""Print a live price board for a mix of shares and indices.

The program builds each instrument once from its exchange, segment and symbol, then reads the last price and the day's open, high, low and previous close from UBI and prints one line per instrument with its change on the day.

Typical usage example:

  .venv/bin/python examples/assets/instruments/instrument/live_price_board.py
"""

from tradingmachine.assets import instruments


class LivePriceBoard:
    """A board of live prices for a fixed list of instruments.

    Attributes:
        board_instruments: A list of tradingmachine.assets.instruments.Instrument, one per row of the board.
    """

    def __init__(self):
        """Looks every instrument on the board up in UBI.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI has no instrument for one of the symbols.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup.
        """
        index_symbols = [
            "NIFTY",
            "BANKNIFTY",
        ]
        share_symbols = [
            "INFY",
            "RELIANCE",
            "HDFCBANK",
        ]
        self.board_instruments = []
        for symbol in index_symbols:
            index = instruments.Instrument(
                exchange="nse",
                segment="equity_indices",
                symbol=symbol,
            )
            self.board_instruments.append(index)
        for symbol in share_symbols:
            share = instruments.Instrument(
                exchange="nse",
                segment="equities",
                symbol=symbol,
            )
            self.board_instruments.append(share)

    def describe(self, instrument: instruments.Instrument) -> str:
        """Builds one line of the board for one instrument.

        Args:
            instrument: The tradingmachine.assets.instruments.Instrument to describe.

        Returns:
            A str with the symbol, last price, day range and change on the day.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI has no quote for the instrument or could not be reached.
        """
        day = instrument.ohlc
        last_price = day["last_price"]
        previous_close = day["previous_close"]
        if last_price is None or not previous_close:
            return f"{instrument.symbol:<12} no price today"
        change_percent = (last_price - previous_close) / previous_close * 100
        day_range = f"{day['ohlc']['low']} - {day['ohlc']['high']}"
        return (
            f"{instrument.symbol:<12} {last_price:>12.2f} "
            f"{day_range:>24} {change_percent:>+8.2f}%"
        )

    def run(self) -> None:
        """Prints the board, one line per instrument.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI has no quote for an instrument or could not be reached.
        """
        print(f"{'Symbol':<12} {'Last':>12} {'Day range':>24} {'Change':>9}")
        for instrument in self.board_instruments:
            print(self.describe(instrument))


if __name__ == "__main__":
    LivePriceBoard().run()
