"""Build a watchlist that names one share twice and handle the BasketMemberError.

A basket may hold each instrument only once. The program builds a watchlist from a list of shares in which IDEA appears twice, catches BasketMemberError, removes the repeat and builds the watchlist again.

Typical usage example:

  .venv/bin/python examples/asset_baskets/exceptions/basket_member_error/add_a_share_to_a_watchlist_twice.py
"""

from tradingmachine.asset_baskets import exceptions
from tradingmachine.asset_baskets import watchlist
from tradingmachine.assets import equities


class DuplicateWatchlist:
    """A watchlist built from a list of shares that repeats one.

    Attributes:
        shares: The list of tradingmachine.assets.equities.Equity, with IDEA twice.
    """

    def __init__(self):
        """Looks the shares up.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup.
        """
        self.shares = []
        for symbol in [
            "IDEA",
            "BHARTIARTL",
            "IDEA",
        ]:
            self.shares.append(equities.Equity(exchange="nse", symbol=symbol))

    def without_repeats(self) -> list[equities.Equity]:
        """Keeps the first of each share.

        Returns:
            The list of tradingmachine.assets.equities.Equity with each instrument once.

        Raises:
            Nothing.
        """
        seen_instrument_ids = set()
        unique_shares = []
        for share in self.shares:
            if share.instrument_id in seen_instrument_ids:
                continue
            seen_instrument_ids.add(share.instrument_id)
            unique_shares.append(share)
        return unique_shares

    def run(self) -> None:
        """Builds the watchlist, recovers from the repeat and prints the members.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: The watchlist without repeats is still refused.
        """
        try:
            telecom_watchlist = watchlist.Watchlist(
                name="Telecom example",
                instruments=self.shares,
            )
        except exceptions.BasketMemberError as error:
            print(f"BasketMemberError: {error}")
            telecom_watchlist = watchlist.Watchlist(
                name="Telecom example",
                instruments=self.without_repeats(),
            )
        print(f"Built {telecom_watchlist!r}")
        for label in telecom_watchlist.labels:
            print(f"  {label}")


if __name__ == "__main__":
    DuplicateWatchlist().run()
