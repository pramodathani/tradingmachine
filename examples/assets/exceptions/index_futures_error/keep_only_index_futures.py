"""Keep only the index futures among several futures contracts, catching InstrumentError.

The program builds an IndexFutures for the nearest NIFTY future, the nearest MCXBULLDEX future, the nearest GOLDM gold future and a NIFTY future on a day nothing expires. The gold future raises IndexFuturesError because gold is not an index, and the missing contract raises the base InstrumentError; one handler for the base class catches both.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/index_futures_error/keep_only_index_futures.py
"""

import datetime

from tradingmachine.assets import commodities
from tradingmachine.assets import equities
from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class IndexFuturesFilter:
    """A filter that keeps only futures written on an index.

    Attributes:
        lookups: The list of (str exchange, str segment, str underlying symbol, datetime.date expiry) tuples to try.
    """

    def __init__(self):
        """Creates the filter with no lookups yet.

        Raises:
            Nothing.
        """
        self.lookups = []

    def collect_lookups(self) -> None:
        """Reads the nearest expiry of each underlying and records the lookups to try.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        nifty_expiry = equities.EquityIndexFutures.expiries("nse", "NIFTY")[0]
        bullion_expiry = commodities.CommodityIndexFutures.expiries(
            "mcx",
            "MCXBULLDEX",
        )[0]
        gold_expiry = commodities.CommodityFutures.expiries("mcx", "GOLDM")[0]
        self.lookups.append(("nse", "equity_index_futures", "NIFTY", nifty_expiry))
        self.lookups.append(
            ("mcx", "commodity_index_futures", "MCXBULLDEX", bullion_expiry)
        )
        self.lookups.append(("mcx", "commodity_futures", "GOLDM", gold_expiry))
        self.lookups.append(
            ("nse", "equity_index_futures", "NIFTY", datetime.date(2026, 12, 25))
        )

    def run(self) -> None:
        """Builds every lookup as an index future and prints which ones are kept.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        self.collect_lookups()
        for exchange, segment, underlying_symbol, expiry_date in self.lookups:
            label = f"{underlying_symbol} {expiry_date}"
            try:
                contract = instruments.IndexFutures(
                    exchange=exchange,
                    segment=segment,
                    underlying_symbol=underlying_symbol,
                    expiry_date=expiry_date,
                )
            except exceptions.InstrumentError as error:
                print(f"Dropped {label}: {type(error).__name__}")
                continue
            print(f"Kept {label}: lot size {contract.lot_size}")


if __name__ == "__main__":
    IndexFuturesFilter().run()
