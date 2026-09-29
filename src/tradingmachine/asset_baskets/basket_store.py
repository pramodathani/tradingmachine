"""Stores baskets in the project's MongoDB and rebuilds them as the right class.

UBI knows nothing about what an index or a fund holds, so baskets are kept in this project's own MongoDB, in the `asset_baskets` collection of the database `tradingmachine.utilities.configuration.Configuration` names. Each document is one version of one basket, identified by its `name` and the `effective_date` it takes effect, because an index is rebalanced and a fund's holdings change every month; `load` finds the version in effect on a given day. A document names each member by its UBI `instrument_id` beside its readable identity fields, and `load` rebuilds every member in one list request.

The `kind` field of a document decides which class `load` builds: `portfolio`, `watchlist`, `index`, `exchange_traded_fund_constituents`, `mutual_fund_constituents`, or `basket` for a plain AssetBasket. `load_for_instrument` finds the basket whose `linked_instrument_id` is a given instrument, which is how `constituents` on an index or a fund finds its contents.

Typical usage example:

  store = basket_store.BasketStore()
  store.save(my_index, effective_date="2026-09-30", source="csv")
  nifty_basket = store.load("NIFTY")
  every_index = store.names(kind="index")
"""

import datetime

import pandas as pd
import pymongo

from tradingmachine.asset_baskets import asset_basket
from tradingmachine.asset_baskets import exceptions
from tradingmachine.asset_baskets import exchange_traded_fund_constituents
from tradingmachine.asset_baskets import index
from tradingmachine.asset_baskets import member_resolver
from tradingmachine.asset_baskets import mutual_fund_constituents
from tradingmachine.asset_baskets import portfolio
from tradingmachine.asset_baskets import watchlist
from tradingmachine.assets import instruments
from tradingmachine.unified_broker_interface import client
from tradingmachine.utilities import configuration

COLLECTION_NAME = "asset_baskets"

HISTORY_COLUMNS = [
    "name",
    "kind",
    "effective_date",
    "source",
    "size",
    "linked_instrument_id",
    "updated_at",
]


class BasketStore:
    """The collection of baskets kept in the project's MongoDB.

    Attributes:
        unified_broker_interface: The client.UnifiedBrokerInterface that rebuilt baskets send their requests through.
    """

    def __init__(
        self,
        project_configuration: configuration.Configuration | None = None,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Initialises the store with the configuration it connects with.

        Args:
            project_configuration: The configuration.Configuration to read the MongoDB settings from, or None to build one that reads the environment and the `.env` file.
            unified_broker_interface: The client.UnifiedBrokerInterface for rebuilt baskets, or None to share the one every instrument uses.

        Raises:
            ValueError: No client was given and the shared client is not configured.
        """
        if project_configuration is None:
            project_configuration = configuration.Configuration()
        self._configuration = project_configuration
        self._resolver = member_resolver.MemberResolver(unified_broker_interface)
        self.unified_broker_interface = self._resolver.unified_broker_interface

    def save(
        self,
        basket: asset_basket.AssetBasket,
        effective_date: datetime.date | str | None = None,
        source: str = "user",
    ) -> dict:
        """Stores a basket as the version of its name in effect from a date, replacing any version already stored for that date.

        Args:
            basket: The asset_basket.AssetBasket to store.
            effective_date: The first day this version is in effect as a datetime.date or a `YYYY-MM-DD` str, or None for today.
            source: The str name of where the members came from, such as `user`, `csv` or `nse`.

        Returns:
            The dict document that was stored.

        Raises:
            ValueError: The project's MongoDB settings are not configured.
            pymongo.errors.PyMongoError: MongoDB could not be reached or refused the write.

        Examples:
            Save a temporary watchlist, print what was stored, and delete it again:

            ```python
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.asset_baskets import watchlist
            from tradingmachine.assets import equities

            shares = [
                equities.Equity(exchange="nse", symbol="IDEA"),
                equities.Equity(exchange="nse", symbol="INFY"),
            ]
            store = basket_store.BasketStore()
            followed = watchlist.Watchlist(
                name="example-watchlist-save", instruments=shares
            )
            document = store.save(followed, source="example")
            try:
                print(document["name"], document["kind"], document["effective_date"])
                print(len(document["members"]))
            finally:
                store.delete(document["name"], document["effective_date"])
            ```

            Save two dated versions of one basket and delete both:

            ```python
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.asset_baskets import watchlist
            from tradingmachine.assets import equities

            shares = [
                equities.Equity(exchange="nse", symbol="IDEA"),
                equities.Equity(exchange="nse", symbol="INFY"),
            ]
            store = basket_store.BasketStore()
            followed = watchlist.Watchlist(
                name="example-watchlist-versions", instruments=shares
            )
            dates = [
                "2026-01-01",
                "2026-07-01",
            ]
            try:
                for effective_date in dates:
                    store.save(followed, effective_date=effective_date)
                print(store.history("example-watchlist-versions")["effective_date"])
            finally:
                for effective_date in dates:
                    store.delete("example-watchlist-versions", effective_date)
            ```
        """
        document = basket.document(effective_date)
        document["source"] = source
        document["updated_at"] = datetime.datetime.now(datetime.UTC)
        with self._mongo_client() as mongo_client:
            collection = self._collection(mongo_client)
            collection.create_index(
                [
                    ("name", pymongo.ASCENDING),
                    ("effective_date", pymongo.ASCENDING),
                ],
                unique=True,
            )
            collection.create_index("linked_instrument_id")
            collection.replace_one(
                {
                    "name": document["name"],
                    "effective_date": document["effective_date"],
                },
                document,
                upsert=True,
            )
        document.pop("_id", None)
        return document

    def load(
        self,
        name: str,
        as_of: datetime.date | str | None = None,
    ) -> asset_basket.AssetBasket:
        """Rebuilds the version of a basket in effect on a day.

        Args:
            name: The str name of the basket.
            as_of: The day as a datetime.date or a `YYYY-MM-DD` str, or None for today.

        Returns:
            The asset_basket.AssetBasket subclass the stored `kind` names, with its members rebuilt in one request.

        Raises:
            BasketNotFoundError: No version of the basket is in effect on that day.
            BasketMemberError: UBI could not find one or more of the stored instruments.
            AssetBasketError: The stored kind is not one this store knows.
            pymongo.errors.PyMongoError: MongoDB could not be reached.

        Examples:
            Save a temporary watchlist, load it back as a Watchlist, and delete it:

            ```python
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.asset_baskets import watchlist
            from tradingmachine.assets import equities

            shares = [
                equities.Equity(exchange="nse", symbol="IDEA"),
                equities.Equity(exchange="nse", symbol="INFY"),
            ]
            store = basket_store.BasketStore()
            followed = watchlist.Watchlist(
                name="example-watchlist-load", instruments=shares
            )
            document = store.save(followed)
            try:
                loaded = store.load("example-watchlist-load")
                print(loaded, loaded.labels)
            finally:
                store.delete(document["name"], document["effective_date"])
            ```

            Handle a basket name that is not stored:

            ```python
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.asset_baskets import exceptions

            store = basket_store.BasketStore()
            try:
                store.load("example-watchlist-never-saved")
            except exceptions.BasketNotFoundError as error:
                print(error)
            ```
        """
        document = self._find_document(
            {
                "name": name,
            },
            as_of,
        )
        if document is None:
            raise exceptions.BasketNotFoundError(
                f"No basket named {name!r} is in effect on {self._date_text(as_of)}"
            )
        return self.build(document)

    def load_for_instrument(
        self,
        instrument: instruments.Instrument,
        as_of: datetime.date | str | None = None,
    ) -> asset_basket.AssetBasket | None:
        """Rebuilds the basket that describes an instrument's contents, such as the members of an index.

        Args:
            instrument: The tradingmachine.assets.instruments.Instrument whose contents to find, which becomes the basket's linked_instrument.
            as_of: The day as a datetime.date or a `YYYY-MM-DD` str, or None for today.

        Returns:
            The asset_basket.AssetBasket subclass the stored `kind` names, or None when no basket describes the instrument on that day.

        Raises:
            BasketMemberError: UBI could not find one or more of the stored instruments.
            AssetBasketError: The stored kind is not one this store knows.
            pymongo.errors.PyMongoError: MongoDB could not be reached.

        Examples:
            Store a temporary index linked to the NIFTY IT index, find it through the index, and delete it:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.asset_baskets import index
            from tradingmachine.assets import equities

            nifty_it = equities.EquityIndex(exchange="nse", symbol="NIFTYIT")
            members = []
            for symbol in [
                "INFY",
                "TCS",
            ]:
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share))
            it_index = index.Index(
                name="example-index-linked",
                members=members,
                weighting="equal",
                linked_instrument=nifty_it,
            )
            store = basket_store.BasketStore()
            document = store.save(it_index)
            try:
                found = store.load_for_instrument(nifty_it)
                print(found, found.linked_instrument.symbol)
            finally:
                store.delete(document["name"], document["effective_date"])
            ```

            See None for an instrument no stored basket describes:

            ```python
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.assets import equities

            idea = equities.Equity(exchange="nse", symbol="IDEA")
            print(basket_store.BasketStore().load_for_instrument(idea))
            ```
        """
        document = self._find_document(
            {
                "linked_instrument_id": instrument.instrument_id,
            },
            as_of,
        )
        if document is None:
            return None
        return self.build(document, linked_instrument=instrument)

    def names(self, kind: str | None = None) -> list[str]:
        """Lists the names of the stored baskets.

        Args:
            kind: The str kind to list, such as `index`, or None for every kind.

        Returns:
            A sorted list of str basket names.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.

        Examples:
            Print the names of every stored basket:

            ```python
            from tradingmachine.asset_baskets import basket_store

            print(basket_store.BasketStore().names())
            ```

            Save a temporary watchlist, find it among the watchlist names, and delete it:

            ```python
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.asset_baskets import watchlist
            from tradingmachine.assets import equities

            shares = [
                equities.Equity(exchange="nse", symbol="IDEA"),
                equities.Equity(exchange="nse", symbol="INFY"),
            ]
            store = basket_store.BasketStore()
            followed = watchlist.Watchlist(
                name="example-watchlist-names", instruments=shares
            )
            document = store.save(followed)
            try:
                print("example-watchlist-names" in store.names(kind="watchlist"))
            finally:
                store.delete(document["name"], document["effective_date"])
            ```
        """
        query = {}
        if kind is not None:
            query["kind"] = kind
        with self._mongo_client() as mongo_client:
            found = self._collection(mongo_client).distinct("name", query)
        return sorted(found)

    def history(self, name: str) -> pd.DataFrame | None:
        """Lists every stored version of a basket.

        Args:
            name: The str name of the basket.

        Returns:
            A pandas.DataFrame with one row per version, oldest first, holding `name`, `kind`, `effective_date`, `source`, `size`, `linked_instrument_id` and `updated_at`, or None when no version is stored.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.

        Examples:
            List the stored versions of a temporary watchlist, then delete them:

            ```python
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.asset_baskets import watchlist
            from tradingmachine.assets import equities

            shares = [
                equities.Equity(exchange="nse", symbol="IDEA"),
                equities.Equity(exchange="nse", symbol="INFY"),
            ]
            store = basket_store.BasketStore()
            followed = watchlist.Watchlist(
                name="example-watchlist-history", instruments=shares
            )
            store.save(followed, effective_date="2026-03-01", source="example")
            store.save(followed, effective_date="2026-06-01", source="example")
            try:
                history = store.history("example-watchlist-history")
                print(history[["name", "effective_date", "source", "size"]])
            finally:
                store.delete("example-watchlist-history", "2026-03-01")
                store.delete("example-watchlist-history", "2026-06-01")
            ```

            See None for a name that was never stored:

            ```python
            from tradingmachine.asset_baskets import basket_store

            print(basket_store.BasketStore().history("example-watchlist-never-saved"))
            ```
        """
        rows = []
        with self._mongo_client() as mongo_client:
            cursor = self._collection(mongo_client).find(
                {
                    "name": name,
                },
                sort=[
                    ("effective_date", pymongo.ASCENDING),
                ],
            )
            for document in cursor:
                rows.append(
                    {
                        "name": document["name"],
                        "kind": document.get("kind"),
                        "effective_date": document["effective_date"],
                        "source": document.get("source"),
                        "size": len(document.get("members", [])),
                        "linked_instrument_id": document.get("linked_instrument_id"),
                        "updated_at": document.get("updated_at"),
                    }
                )
        if not rows:
            return None
        return pd.DataFrame(rows, columns=HISTORY_COLUMNS)

    def delete(self, name: str, effective_date: datetime.date | str) -> bool:
        """Deletes one stored version of a basket.

        Args:
            name: The str name of the basket.
            effective_date: The version's effective date as a datetime.date or a `YYYY-MM-DD` str.

        Returns:
            A bool that is True when a version was deleted and False when none matched.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.

        Examples:
            Save a temporary watchlist and delete it, which answers True:

            ```python
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.asset_baskets import watchlist
            from tradingmachine.assets import equities

            shares = [
                equities.Equity(exchange="nse", symbol="IDEA"),
                equities.Equity(exchange="nse", symbol="INFY"),
            ]
            store = basket_store.BasketStore()
            followed = watchlist.Watchlist(
                name="example-watchlist-delete", instruments=shares
            )
            document = store.save(followed, effective_date="2026-09-01")
            print(store.delete("example-watchlist-delete", "2026-09-01"))
            ```

            See False for a version that is not stored:

            ```python
            import datetime

            from tradingmachine.asset_baskets import basket_store

            store = basket_store.BasketStore()
            print(store.delete("example-watchlist-missing", datetime.date(2026, 9, 1)))
            ```
        """
        with self._mongo_client() as mongo_client:
            outcome = self._collection(mongo_client).delete_one(
                {
                    "name": name,
                    "effective_date": self._date_text(effective_date),
                }
            )
        return outcome.deleted_count == 1

    def build(
        self,
        document: dict,
        linked_instrument: instruments.Instrument | None = None,
    ) -> asset_basket.AssetBasket:
        """Builds the basket a stored document describes, as the class its `kind` names.

        Args:
            document: A dict in the form AssetBasket.document gives, with a `members` list naming each instrument.
            linked_instrument: The tradingmachine.assets.instruments.Instrument to link the basket to, or None to look up the document's `linked_instrument_id` when it has one.

        Returns:
            The asset_basket.AssetBasket subclass the document's `kind` names.

        Raises:
            BasketMemberError: The document has no members, or UBI could not find one or more of its instruments.
            AssetBasketError: The document's kind is not one this store knows.

        Examples:
            Build an equal-weighted index from a hand-written document without storing it:

            ```python
            from tradingmachine.asset_baskets import basket_store

            document = {
                "name": "two IT shares",
                "kind": "index",
                "weighting": "equal",
                "members": [
                    {
                        "exchange": "nse",
                        "segment": "equities",
                        "symbol": "INFY",
                    },
                    {
                        "exchange": "nse",
                        "segment": "equities",
                        "symbol": "TCS",
                    },
                ],
            }
            basket = basket_store.BasketStore().build(document)
            print(basket, basket.weights.to_dict())
            ```

            See a document with a kind the store does not know refused:

            ```python
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.asset_baskets import exceptions

            document = {
                "name": "mystery",
                "kind": "hedge_fund",
                "members": [
                    {
                        "exchange": "nse",
                        "segment": "equities",
                        "symbol": "INFY",
                    },
                ],
            }
            try:
                basket_store.BasketStore().build(document)
            except exceptions.AssetBasketError as error:
                print(error)
            ```
        """
        members = self._resolver.resolve(document.get("members", []))
        if linked_instrument is None and document.get("linked_instrument_id"):
            linked_instrument = self._resolver.resolve_one(
                {
                    "instrument_id": document["linked_instrument_id"],
                }
            )
        kind = document.get("kind", asset_basket.AssetBasket.KIND)
        name = document["name"]
        unmapped_weight = document.get("unmapped_weight") or 0.0
        if kind == portfolio.Portfolio.KIND:
            return portfolio.Portfolio(
                name=name,
                members=members,
                unified_broker_interface=self.unified_broker_interface,
            )
        if kind == watchlist.Watchlist.KIND:
            held_instruments = []
            for member in members:
                held_instruments.append(member.instrument)
            return watchlist.Watchlist(
                name=name,
                instruments=held_instruments,
                unified_broker_interface=self.unified_broker_interface,
            )
        if kind == index.Index.KIND:
            return index.Index(
                name=name,
                members=members,
                weighting=document.get("weighting") or index.STATED_WEIGHTING,
                base_value=document.get("base_value")
                or asset_basket.DEFAULT_BASE_VALUE,
                base_date=document.get("base_date"),
                linked_instrument=linked_instrument,
                unified_broker_interface=self.unified_broker_interface,
            )
        if (
            kind
            == exchange_traded_fund_constituents.ExchangeTradedFundConstituents.KIND
        ):
            indicative_net_asset_value = None
            if document.get("indicative_net_asset_value_instrument_id"):
                indicative_net_asset_value = self._resolver.resolve_one(
                    {
                        "instrument_id": document[
                            "indicative_net_asset_value_instrument_id"
                        ],
                    }
                )
            return exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name=name,
                members=members,
                fund=linked_instrument,
                indicative_net_asset_value=indicative_net_asset_value,
                unmapped_weight=unmapped_weight,
                unified_broker_interface=self.unified_broker_interface,
            )
        if kind == mutual_fund_constituents.MutualFundConstituents.KIND:
            return mutual_fund_constituents.MutualFundConstituents(
                name=name,
                members=members,
                fund=linked_instrument,
                unmapped_weight=unmapped_weight,
                unified_broker_interface=self.unified_broker_interface,
            )
        if kind == asset_basket.AssetBasket.KIND:
            return asset_basket.AssetBasket(
                name=name,
                members=members,
                linked_instrument=linked_instrument,
                unmapped_weight=unmapped_weight,
                unified_broker_interface=self.unified_broker_interface,
            )
        raise exceptions.AssetBasketError(
            f"The basket {name!r} is stored with a kind this store does not know: {kind=}"
        )

    def _find_document(
        self,
        query: dict,
        as_of: datetime.date | str | None,
    ) -> dict | None:
        """Finds the latest stored version matching a query that is in effect on a day.

        Args:
            query: A dict MongoDB query, such as one on `name` or `linked_instrument_id`.
            as_of: The day as a datetime.date or a `YYYY-MM-DD` str, or None for today.

        Returns:
            The dict document, or None when no matching version is in effect on that day.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.
        """
        dated_query = dict(query)
        dated_query["effective_date"] = {
            "$lte": self._date_text(as_of),
        }
        with self._mongo_client() as mongo_client:
            return self._collection(mongo_client).find_one(
                dated_query,
                sort=[
                    ("effective_date", pymongo.DESCENDING),
                ],
            )

    def _mongo_client(self) -> pymongo.MongoClient:
        """Opens a client to the project's MongoDB, to be closed with a `with` block.

        Returns:
            A pymongo.MongoClient.

        Raises:
            ValueError: The project's MongoDB settings are not configured.
        """
        return pymongo.MongoClient(self._configuration.mongodb_connection_string)

    def _collection(self, mongo_client: pymongo.MongoClient):
        """Picks the baskets collection out of an open client.

        Args:
            mongo_client: An open pymongo.MongoClient.

        Returns:
            The pymongo.collection.Collection that holds the baskets.

        Raises:
            ValueError: The project's MongoDB database name is not configured.
        """
        database_name = self._configuration.mongodb_database_name
        if not database_name:
            raise ValueError("The project's MongoDB database name is not configured")
        return mongo_client[database_name][COLLECTION_NAME]

    @staticmethod
    def _date_text(value: datetime.date | str | None) -> str:
        """Turns a day into the `YYYY-MM-DD` form the documents store, defaulting to today.

        Args:
            value: A datetime.date, a `YYYY-MM-DD` str, or None for today.

        Returns:
            The str date in `YYYY-MM-DD` form.

        Raises:
            Nothing.
        """
        if value is None:
            return datetime.date.today().isoformat()
        if isinstance(value, datetime.date):
            return value.isoformat()
        return value
