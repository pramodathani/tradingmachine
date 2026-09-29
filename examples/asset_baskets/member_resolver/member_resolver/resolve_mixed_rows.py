"""Turn rows naming shares, a fund and an index into basket members with one request.

The program describes a small allocation as plain rows, the way a stored basket or a CSV file does: two shares and a gold fund by exchange, segment and symbol, and the NIFTY index by the instrument id a previous lookup gave. It resolves every row in one request to UBI and prints each member with the class of instrument it became and its last price.

Typical usage example:

  .venv/bin/python examples/asset_baskets/member_resolver/member_resolver/resolve_mixed_rows.py
"""

from tradingmachine.asset_baskets import member_resolver


class ResolveMixedRows:
    """A resolver run over rows of several kinds.

    Attributes:
        resolver: The tradingmachine.asset_baskets.member_resolver.MemberResolver that looks the rows up.
    """

    def __init__(self):
        """Creates the resolver on the shared UBI client.

        Raises:
            ValueError: The shared UBI client is not configured.
        """
        self.resolver = member_resolver.MemberResolver()

    def rows(self) -> list[dict]:
        """Builds the rows, looking the NIFTY index up first to name it by its id.

        Returns:
            A list of dicts, each naming one instrument and giving its weight.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: UBI could not find the NIFTY index.
        """
        nifty = self.resolver.resolve_one(
            {
                "exchange": "nse",
                "segment": "equity_indices",
                "symbol": "NIFTY",
            }
        )
        return [
            {
                "exchange": "nse",
                "segment": "equities",
                "symbol": "INFY",
                "weight": 40,
            },
            {
                "exchange": "nse",
                "segment": "equities",
                "symbol": "HDFCBANK",
                "weight": 30,
            },
            {
                "exchange": "nse",
                "segment": "exchange_traded_funds",
                "symbol": "GOLDBEES",
                "weight": 20,
            },
            {
                "instrument_id": nifty.instrument_id,
                "weight": 10,
            },
        ]

    def run(self) -> None:
        """Resolves the rows and prints each member.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: UBI could not find one of the instruments.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        members = self.resolver.resolve(self.rows())
        for member in members:
            kind = type(member.instrument).__name__
            print(
                f"{member.label:<16} {kind:<24} weight {member.weight:>3}  last {member.instrument.last_price}"
            )


if __name__ == "__main__":
    ResolveMixedRows().run()
