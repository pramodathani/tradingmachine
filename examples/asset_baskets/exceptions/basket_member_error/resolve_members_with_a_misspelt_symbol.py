"""Resolve basket members from rows with a misspelt symbol, catching AssetBasketError.

MemberResolver looks every row up in UBI in one request and raises BasketMemberError listing every row UBI could not find. The program resolves four rows, one of them misspelt, catches the error through its base class AssetBasketError, and resolves each row on its own to find which ones work.

Typical usage example:

  .venv/bin/python examples/asset_baskets/exceptions/basket_member_error/resolve_members_with_a_misspelt_symbol.py
"""

from tradingmachine.asset_baskets import exceptions
from tradingmachine.asset_baskets import member_resolver


class MisspeltMemberResolution:
    """A resolution of basket rows, one of which names a share UBI does not know.

    Attributes:
        resolver: The tradingmachine.asset_baskets.member_resolver.MemberResolver that looks the rows up.
        rows: The list of dict rows to resolve.
    """

    def __init__(self):
        """Creates the resolver and the rows.

        Raises:
            ValueError: The shared client is not configured.
        """
        self.resolver = member_resolver.MemberResolver()
        self.rows = []
        for symbol in [
            "IDEA",
            "BHARTIARTL",
            "INDUSTOWERS",
            "TATACOMM",
        ]:
            self.rows.append(
                {
                    "exchange": "nse",
                    "segment": "equities",
                    "symbol": symbol,
                }
            )

    def run(self) -> None:
        """Resolves all rows at once, and one by one when that fails, printing the outcome.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        try:
            members = self.resolver.resolve(self.rows)
        except exceptions.AssetBasketError as error:
            print(f"{type(error).__name__}: {error}")
        else:
            print(f"Resolved all {len(members)} members.")
            return
        for row in self.rows:
            try:
                instrument = self.resolver.resolve_one(row)
            except exceptions.AssetBasketError:
                print(f"{row['symbol']}: not found")
                continue
            print(f"{row['symbol']}: {instrument.instrument_id}")


if __name__ == "__main__":
    MisspeltMemberResolution().run()
