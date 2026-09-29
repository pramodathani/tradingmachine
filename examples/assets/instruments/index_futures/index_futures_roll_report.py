"""Report the cost of rolling the nearest index futures into the next expiry.

The program builds the nearest and the next future on each of two indices through the base IndexFutures class, from the instrument ids that the discovery call lists, and prints the spread between them, which is what a trader pays or receives to roll a position forward.

Typical usage example:

  .venv/bin/python examples/assets/instruments/index_futures/index_futures_roll_report.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import instruments


class IndexFuturesRollReport:
    """The roll spread of the nearest index futures.

    Attributes:
        symbols: A list of str index symbols to report on.
    """

    def __init__(self):
        """Stores the indices to report on.

        Raises:
            Nothing.
        """
        self.symbols = [
            "NIFTY",
            "BANKNIFTY",
        ]

    def report(self, symbol: str) -> None:
        """Prints the roll of one index's nearest future.

        Args:
            symbol: The str symbol of the index.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        contracts = equities.EquityIndexFutures.contracts(
            exchange="nse",
            underlying_symbol=symbol,
        )
        if contracts is None or len(contracts) < 2:
            print(f"{symbol}: fewer than two live futures")
            return
        near = instruments.IndexFutures(
            instrument_id=contracts["instrument_id"].iloc[0]
        )
        far = instruments.IndexFutures(instrument_id=contracts["instrument_id"].iloc[1])
        near_price = near.last_price
        far_price = far.last_price
        print(
            f"{symbol}: {near.expiry_date} at {near_price}, {far.expiry_date} at {far_price}"
        )
        if near_price is None or far_price is None:
            print("  a last price is missing")
            return
        spread = far_price - near_price
        print(
            f"  roll spread {spread:.2f} points, Rs {spread * near.lot_size:,.0f} a lot"
        )

    def run(self) -> None:
        """Prints the roll of every index.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        for symbol in self.symbols:
            self.report(symbol)


if __name__ == "__main__":
    IndexFuturesRollReport().run()
