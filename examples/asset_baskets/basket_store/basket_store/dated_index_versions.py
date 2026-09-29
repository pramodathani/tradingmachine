"""Keep two dated versions of an index and load the one in effect on a given day.

The program stores two versions of an equal-weighted index under the temporary name `example-index-versions`: one from 1 January 2026 with two shares and one from 1 July 2026 with a third share added. It prints the stored history, loads the version in effect on 1 March and on today, and deletes both versions before it ends, whatever happens.

Typical usage example:

  .venv/bin/python examples/asset_baskets/basket_store/basket_store/dated_index_versions.py
"""

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import basket_store
from tradingmachine.asset_baskets import index
from tradingmachine.assets import equities

NAME = "example-index-versions"

FIRST_DATE = "2026-01-01"

SECOND_DATE = "2026-07-01"


class DatedIndexVersions:
    """Two stored versions of one index, as after a rebalance.

    Attributes:
        store: The tradingmachine.asset_baskets.basket_store.BasketStore the versions are saved in.
    """

    def __init__(self):
        """Creates the store.

        Raises:
            ValueError: The shared UBI client is not configured.
        """
        self.store = basket_store.BasketStore()

    def build_index(self, symbols: list[str]) -> index.Index:
        """Builds an equal-weighted index of NSE shares.

        Args:
            symbols: The list of str NSE symbols to include.

        Returns:
            The tradingmachine.asset_baskets.index.Index of those shares.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
        """
        members = []
        for symbol in symbols:
            share = equities.Equity(exchange="nse", symbol=symbol)
            members.append(basket_member.BasketMember(share))
        return index.Index(name=NAME, members=members, weighting="equal")

    def run(self) -> None:
        """Saves both versions, prints the history and two loads, then deletes both.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        first_version = self.build_index(
            [
                "INFY",
                "TCS",
            ]
        )
        second_version = self.build_index(
            [
                "INFY",
                "TCS",
                "HCLTECH",
            ]
        )
        try:
            self.store.save(first_version, effective_date=FIRST_DATE, source="example")
            self.store.save(
                second_version, effective_date=SECOND_DATE, source="example"
            )
            history = self.store.history(NAME)
            print(history[["name", "kind", "effective_date", "size"]])
            in_march = self.store.load(NAME, as_of="2026-03-01")
            print(f"In effect on 2026-03-01: {in_march.labels}")
            today = self.store.load(NAME)
            print(f"In effect today: {today.labels}")
        finally:
            for effective_date in [
                FIRST_DATE,
                SECOND_DATE,
            ]:
                self.store.delete(NAME, effective_date)
            print(f"History after deleting: {self.store.history(NAME)}")


if __name__ == "__main__":
    DatedIndexVersions().run()
