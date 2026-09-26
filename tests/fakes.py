"""Stand-ins for MongoDB, Redis and the clock, shared by the tests.

Typical usage example:

  monkeypatch.setattr(pymongo, "MongoClient", fakes.FakeMongoClientFactory(documents))
"""

from typing import Any

from tests import fake_ubi_server


class FakeCollection:
    """A MongoDB collection holding a list of documents.

    Attributes:
        documents: A list of dict documents.
        queries: A list of the dict filters passed to find_one, in order.
    """

    def __init__(self, documents: list[dict]):
        """Initialises the collection.

        Args:
            documents: A list of dict documents.

        Raises:
            Nothing.
        """
        self.documents = documents
        self.queries = []

    def find_one(self, query: dict, projection: dict | None = None) -> dict | None:
        """Finds the first document whose fields match every field of the query.

        Args:
            query: A dict of field names and the values they must equal.
            projection: A dict projection, which is ignored apart from `_id`.

        Returns:
            A copy of the matching dict document, or None.

        Raises:
            Nothing.
        """
        self.queries.append(query)
        for document in self.documents:
            matches = True
            for name, value in query.items():
                if document.get(name) != value:
                    matches = False
            if matches:
                found = dict(document)
                if projection is not None and projection.get("_id") == 0:
                    found.pop("_id", None)
                return found
        return None


class FakeMongoClient:
    """A MongoDB client whose databases hold prepared collections.

    Attributes:
        databases: A dict of database name to a dict of collection name to FakeCollection.
        closed: A bool that is True once the client has been closed.
        arguments: A tuple of the positional arguments the client was created with.
        keyword_arguments: A dict of the keyword arguments the client was created with.
    """

    def __init__(
        self,
        databases: dict,
        arguments: tuple,
        keyword_arguments: dict,
    ):
        """Initialises the client.

        Args:
            databases: A dict of database name to a dict of collection name to FakeCollection.
            arguments: A tuple of the positional arguments pymongo.MongoClient was called with.
            keyword_arguments: A dict of the keyword arguments pymongo.MongoClient was called with.

        Raises:
            Nothing.
        """
        self.databases = databases
        self.closed = False
        self.arguments = arguments
        self.keyword_arguments = keyword_arguments

    def __getitem__(self, database_name: str) -> dict:
        """Returns one database.

        Args:
            database_name: The str database name.

        Returns:
            A dict of collection name to FakeCollection, empty when the database is unknown.

        Raises:
            Nothing.
        """
        return self.databases.setdefault(database_name, {})

    def __enter__(self) -> "FakeMongoClient":
        """Opens the client for a `with` block.

        Returns:
            This FakeMongoClient.

        Raises:
            Nothing.
        """
        return self

    def __exit__(self, *exception_information: Any) -> None:
        """Closes the client at the end of a `with` block.

        Args:
            *exception_information: The exception type, value and traceback, or three Nones.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.close()

    def close(self) -> None:
        """Closes the client.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.closed = True


class FakeMongoClientFactory:
    """A replacement for pymongo.MongoClient that hands out FakeMongoClient objects over shared databases.

    Attributes:
        databases: A dict of database name to a dict of collection name to FakeCollection.
        clients: A list of every FakeMongoClient created, in order.
    """

    def __init__(self, databases: dict):
        """Initialises the factory.

        Args:
            databases: A dict of database name to a dict of collection name to FakeCollection.

        Raises:
            Nothing.
        """
        self.databases = databases
        self.clients = []

    def __call__(self, *arguments: Any, **keyword_arguments: Any) -> FakeMongoClient:
        """Creates a client, as pymongo.MongoClient would.

        Args:
            *arguments: The positional arguments given to pymongo.MongoClient.
            **keyword_arguments: The keyword arguments given to pymongo.MongoClient.

        Returns:
            A new FakeMongoClient over the shared databases.

        Raises:
            Nothing.
        """
        created = FakeMongoClient(self.databases, arguments, keyword_arguments)
        self.clients.append(created)
        return created


class SettingsDatabase:
    """Builds the databases a FakeMongoClientFactory serves, holding UBI's api key and secret."""

    @staticmethod
    def with_credentials(database_name: str) -> dict:
        """Builds databases whose `settings` collection holds the fake server's key and secret.

        Args:
            database_name: The str name of the database.

        Returns:
            A dict of database name to a dict of collection name to FakeCollection.

        Raises:
            Nothing.
        """
        settings = FakeCollection(
            [
                {
                    "_id": "settings-document",
                    "broker_name": "unified_broker_interface",
                    "api_key": fake_ubi_server.API_KEY,
                    "api_secret": fake_ubi_server.API_SECRET,
                },
            ]
        )
        return {
            database_name: {
                "settings": settings,
            },
        }


class FixedClock:
    """A clock that reports a time the test sets.

    Attributes:
        current: The float time in epoch seconds that now reports.
    """

    def __init__(self, current: float):
        """Initialises the clock.

        Args:
            current: The float time in epoch seconds.

        Raises:
            Nothing.
        """
        self.current = current

    def now(self) -> float:
        """Reports the set time.

        Returns:
            The float time in epoch seconds.

        Raises:
            Nothing.
        """
        return self.current
