"""Stand-ins for MongoDB, Redis and the clock, shared by the tests.

Typical usage example:

  monkeypatch.setattr(pymongo, "MongoClient", fakes.FakeMongoClientFactory(documents))
"""

import json
from typing import Any

import pymongo.errors
import redis

from tests import fake_ubi_server


class FakeCollection:
    """A MongoDB collection holding a list of documents.

    Attributes:
        documents: A list of dict documents.
        queries: A list of the dict filters passed to find_one, in order.
        failing: A bool that is True to make find_one raise pymongo.errors.ServerSelectionTimeoutError.
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
        self.failing = False

    def find_one(self, query: dict, projection: dict | None = None) -> dict | None:
        """Finds the first document whose fields match every field of the query.

        Args:
            query: A dict of field names and the values they must equal.
            projection: A dict projection, which is ignored apart from `_id`.

        Returns:
            A copy of the matching dict document, or None.

        Raises:
            pymongo.errors.ServerSelectionTimeoutError: The collection is set to fail.
        """
        self.queries.append(query)
        if self.failing:
            raise pymongo.errors.ServerSelectionTimeoutError(
                "MongoDB is down in this test"
            )
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


class FakeRedisClient:
    """A Redis client over prepared hashes, offering only the reads the library uses.

    Attributes:
        hashes: A dict of hash name to a dict of field to str value.
        failing: A bool that is True to make every command raise redis.ConnectionError.
        commands: A list of tuples (command name, hash name, fields) in the order received.
        closed: A bool that is True once the client has been closed.
        keyword_arguments: A dict of the keyword arguments the client was created with.
    """

    def __init__(self, hashes: dict, keyword_arguments: dict):
        """Initialises the client.

        Args:
            hashes: A dict of hash name to a dict of field to str value, shared with the factory.
            keyword_arguments: A dict of the keyword arguments redis.Redis was called with.

        Raises:
            Nothing.
        """
        self.hashes = hashes
        self.failing = False
        self.commands = []
        self.closed = False
        self.keyword_arguments = keyword_arguments

    def hget(self, name: str, field: str) -> str | None:
        """Reads one field of a hash.

        Args:
            name: The str hash name.
            field: The str field.

        Returns:
            The str value, or None when the hash or field does not exist.

        Raises:
            redis.ConnectionError: The client is set to fail.
        """
        self._check("hget", name, [field])
        return self.hashes.get(name, {}).get(field)

    def hmget(self, name: str, fields: list[str]) -> list[str | None]:
        """Reads several fields of a hash.

        Args:
            name: The str hash name.
            fields: A list of str fields.

        Returns:
            A list of str values or None, one per field, in order.

        Raises:
            redis.ConnectionError: The client is set to fail.
        """
        self._check("hmget", name, list(fields))
        stored = self.hashes.get(name, {})
        values = []
        for field in fields:
            values.append(stored.get(field))
        return values

    def close(self) -> None:
        """Closes the client.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.closed = True

    def _check(self, command: str, name: str, fields: list[str]) -> None:
        """Records a command and raises when the client is set to fail.

        Args:
            command: The str command name.
            name: The str hash name.
            fields: A list of the str fields.

        Returns:
            None.

        Raises:
            redis.ConnectionError: The client is set to fail.
        """
        self.commands.append((command, name, fields))
        if self.failing:
            raise redis.ConnectionError("Redis is down in this test")


class FakeRedisFactory:
    """A replacement for redis.Redis that hands out FakeRedisClient objects over shared hashes.

    Attributes:
        hashes: A dict of hash name to a dict of field to str value.
        clients: A list of every FakeRedisClient created, in order.
    """

    def __init__(self):
        """Initialises the factory with no hashes.

        Raises:
            Nothing.
        """
        self.hashes = {}
        self.clients = []

    def __call__(self, **keyword_arguments: Any) -> FakeRedisClient:
        """Creates a client, as redis.Redis would.

        Args:
            **keyword_arguments: The keyword arguments given to redis.Redis.

        Returns:
            A new FakeRedisClient over the shared hashes.

        Raises:
            Nothing.
        """
        created = FakeRedisClient(self.hashes, keyword_arguments)
        self.clients.append(created)
        return created

    def set_failing(self, failing: bool) -> None:
        """Makes every client created so far fail, or work again.

        Args:
            failing: A bool that is True to make commands raise.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for created in self.clients:
            created.failing = failing

    def store_json(self, name: str, field: str, value: Any) -> None:
        """Stores a value as JSON in one field of a hash.

        Args:
            name: The str hash name.
            field: The str field.
            value: The value, of any JSON type.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.hashes.setdefault(name, {})[field] = json.dumps(value)


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

    def advance(self, seconds: float) -> None:
        """Moves the clock forward.

        Args:
            seconds: The float number of seconds to move by.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.current += seconds
