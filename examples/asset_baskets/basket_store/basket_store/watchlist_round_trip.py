"""Store a watchlist in MongoDB, read it back, and remove it.

The program builds a watchlist of three shares under the temporary name `example-watchlist-round-trip`, saves it through `BasketStore`, lists the stored watchlists, loads it back as a `Watchlist`, ranks its members by today's move, and deletes the stored copy before it ends, whatever happens.

Typical usage example:

  .venv/bin/python examples/asset_baskets/basket_store/basket_store/watchlist_round_trip.py
"""

from tradingmachine.asset_baskets import basket_store
from tradingmachine.asset_baskets import watchlist
from tradingmachine.assets import equities

NAME = "example-watchlist-round-trip"

SYMBOLS = [
    "IDEA",
    "INFY",
    "SBIN",
]


class WatchlistRoundTrip:
    """A watchlist saved to the basket store and loaded back.

    Attributes:
        store: The tradingmachine.asset_baskets.basket_store.BasketStore the watchlist is saved in.
        followed: The tradingmachine.asset_baskets.watchlist.Watchlist that is saved.
    """

    def __init__(self):
        """Looks the shares up in UBI and builds the watchlist.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
        """
        self.store = basket_store.BasketStore()
        shares = []
        for symbol in SYMBOLS:
            shares.append(equities.Equity(exchange="nse", symbol=symbol))
        self.followed = watchlist.Watchlist(name=NAME, instruments=shares)

    def run(self) -> None:
        """Saves, lists, loads and ranks the watchlist, then deletes it.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        document = self.store.save(self.followed, source="example")
        print(f"Saved {document['name']} for {document['effective_date']}")
        try:
            print(f"Stored watchlists: {self.store.names(kind='watchlist')}")
            loaded = self.store.load(NAME)
            print(f"Loaded {loaded} with {loaded.labels}")
            ranked = loaded.rank_by("change_percent")
            print(ranked[["label", "last_price", "change_percent"]])
        finally:
            deleted = self.store.delete(document["name"], document["effective_date"])
            print(f"Deleted the stored copy: {deleted}")


if __name__ == "__main__":
    WatchlistRoundTrip().run()
