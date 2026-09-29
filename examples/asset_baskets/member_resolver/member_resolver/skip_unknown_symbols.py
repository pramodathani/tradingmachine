"""Resolve a list of symbols, report the ones UBI does not know, and keep the rest.

The program tries to resolve a watch list typed by hand, which contains one misspelt symbol and one that was renamed. `MemberResolver.resolve` refuses the whole list and names every failure in one error, so the program then resolves each symbol on its own with `resolve_one`, keeps the ones UBI knows, and prints both groups.

Typical usage example:

  .venv/bin/python examples/asset_baskets/member_resolver/member_resolver/skip_unknown_symbols.py
"""

from tradingmachine.asset_baskets import exceptions
from tradingmachine.asset_baskets import member_resolver

SYMBOLS = [
    "INFY",
    "TCS",
    "INFOSYS",
    "SBIN",
    "HDFC",
]


class SkipUnknownSymbols:
    """A resolver run that separates the symbols UBI knows from the ones it does not.

    Attributes:
        resolver: The tradingmachine.asset_baskets.member_resolver.MemberResolver that looks the symbols up.
    """

    def __init__(self):
        """Creates the resolver on the shared UBI client.

        Raises:
            ValueError: The shared UBI client is not configured.
        """
        self.resolver = member_resolver.MemberResolver()

    def row_for(self, symbol: str) -> dict:
        """Describes one NSE share as a row.

        Args:
            symbol: The str NSE symbol.

        Returns:
            A dict with `exchange`, `segment` and `symbol`.

        Raises:
            Nothing.
        """
        return {
            "exchange": "nse",
            "segment": "equities",
            "symbol": symbol,
        }

    def run(self) -> None:
        """Tries the whole list, then each symbol alone, and prints what was found.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        rows = []
        for symbol in SYMBOLS:
            rows.append(self.row_for(symbol))
        try:
            self.resolver.resolve(rows)
            print("Every symbol is known.")
            return
        except exceptions.BasketMemberError as error:
            print(f"The whole list was refused: {error}")
        known = []
        unknown = []
        for symbol in SYMBOLS:
            try:
                instrument = self.resolver.resolve_one(self.row_for(symbol))
            except exceptions.BasketMemberError:
                unknown.append(symbol)
                continue
            known.append(instrument.symbol)
        print(f"Known: {known}")
        print(f"Unknown: {unknown}")


if __name__ == "__main__":
    SkipUnknownSymbols().run()
