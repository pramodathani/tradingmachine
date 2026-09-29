"""Build instruments of several families from typed input, catching InstrumentError once for all of them.

Every family error, such as EquityError, CommodityFuturesError or MutualFundError, is a subclass of InstrumentError. The program builds a share, an index, a commodity and a mutual fund scheme from a list in which some names are wrong, and one handler for InstrumentError catches whichever family error each wrong name raises.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/instrument_error/build_a_watch_list_from_mixed_input.py
"""

from tradingmachine.assets import commodities
from tradingmachine.assets import equities
from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments
from tradingmachine.assets import mutual_funds


class MixedWatchList:
    """A watch list built from names of several asset families.

    Attributes:
        requests: The list of (str family, str exchange, str symbol) tuples to build, as a person typed them.
        built_instruments: The list of tradingmachine.assets.instruments.Instrument that were found.
    """

    def __init__(self):
        """Creates the watch list with the names to build.

        Raises:
            Nothing.
        """
        self.requests = [
            ("share", "nse", "IDEA"),
            ("share", "nse", "VODAFONE"),
            ("index", "nse", "NIFTY"),
            ("commodity", "mcx", "GOLDMINI"),
            ("mutual fund", "nse", "ABSLFTTIDG"),
            ("mutual fund", "nse", "ABSL FLEXI"),
        ]
        self.built_instruments = []

    def build(self, family: str, exchange: str, symbol: str) -> instruments.Instrument:
        """Builds one instrument of the named family.

        Args:
            family: The str family, `share`, `index`, `commodity` or `mutual fund`.
            exchange: The str exchange the instrument is listed on.
            symbol: The str symbol of the instrument.

        Returns:
            The tradingmachine.assets.instruments.Instrument of the family's own class.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know the instrument, raised as the family's own subclass.
            ValueError: The family is not one this program knows.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        if family == "share":
            return equities.Equity(exchange=exchange, symbol=symbol)
        if family == "index":
            return equities.EquityIndex(exchange=exchange, symbol=symbol)
        if family == "commodity":
            return commodities.Commodity(exchange=exchange, symbol=symbol)
        if family == "mutual fund":
            return mutual_funds.MutualFund(exchange=exchange, symbol=symbol)
        raise ValueError(f"Not a family this program knows: {family=}")

    def run(self) -> None:
        """Builds every requested instrument and prints what was found and what was not.

        Returns:
            None.

        Raises:
            ValueError: A request names a family this program does not know.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup.
        """
        for family, exchange, symbol in self.requests:
            try:
                instrument = self.build(family, exchange, symbol)
            except exceptions.InstrumentError as error:
                print(f"Skipped {family} {symbol!r}: {type(error).__name__}: {error}")
                continue
            self.built_instruments.append(instrument)
            print(f"Added {instrument!r}")
        print(
            f"The watch list holds {len(self.built_instruments)} of {len(self.requests)} requested instruments."
        )


if __name__ == "__main__":
    MixedWatchList().run()
