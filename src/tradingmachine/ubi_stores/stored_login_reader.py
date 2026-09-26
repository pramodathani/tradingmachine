"""Reads UBI's stored login and api credentials from UBI's own Redis and MongoDB, never writing to either.

UBI keeps its current access token in the Redis hash `last_login`, under the field `unified_broker_interface`, and the same document in its MongoDB collection `last_login`. Its api key and secret are in the MongoDB collection `settings`. This reader reads those three things and nothing else.

Typical usage example:

  reader = StoredLoginReader(redis_settings, mongo_settings)
  login = reader.stored_login()
  reader.close()
"""

import json
import logging

import pymongo
import pymongo.errors
import redis

from tradingmachine.ubi_client import exceptions
from tradingmachine.ubi_stores import store_settings
from tradingmachine.ubi_stores import stored_login

LOGIN_HASH = "last_login"

APPLICATION_NAME = "unified_broker_interface"

LOGIN_COLLECTION = "last_login"

SETTINGS_COLLECTION = "settings"

LOGGER = logging.getLogger(__name__)


class StoredLoginReader:
    """Read-only access to the login UBI has stored and the api key and secret it checks connects against."""

    def __init__(
        self,
        redis_settings: store_settings.RedisSettings,
        mongo_settings: store_settings.MongoSettings,
    ):
        """Initialises the reader; neither store is contacted until the first read.

        Args:
            redis_settings: The store_settings.RedisSettings of UBI's Redis.
            mongo_settings: The store_settings.MongoSettings of UBI's MongoDB.

        Raises:
            Nothing.
        """
        self._redis_client = redis.Redis(
            host=redis_settings.host,
            port=redis_settings.port,
            db=redis_settings.database,
            username=redis_settings.username,
            password=redis_settings.password,
            decode_responses=True,
            socket_timeout=redis_settings.timeout_seconds,
            socket_connect_timeout=redis_settings.timeout_seconds,
        )
        timeout_milliseconds = int(mongo_settings.timeout_seconds * 1000)
        self._mongo_client = pymongo.MongoClient(
            host=mongo_settings.host,
            port=mongo_settings.port,
            username=mongo_settings.username,
            password=mongo_settings.password,
            serverSelectionTimeoutMS=timeout_milliseconds,
            connectTimeoutMS=timeout_milliseconds,
            socketTimeoutMS=timeout_milliseconds,
        )
        self._mongo_database_name = mongo_settings.database_name

    def stored_login(self) -> stored_login.StoredLogin | None:
        """Reads UBI's stored login, from Redis first and MongoDB second.

        Redis is the copy UBI itself checks on every request; MongoDB is the record it is copied from, used here when Redis has no readable login.

        Returns:
            The stored_login.StoredLogin, or None when neither store has one.

        Raises:
            UnreachableError: Redis had no readable login and MongoDB could not be read.
        """
        document = self._redis_login()
        if document is None:
            try:
                document = self._find_application_document(LOGIN_COLLECTION)
            except pymongo.errors.PyMongoError as error:
                raise exceptions.UnreachableError(
                    "UBI Redis had no readable login and UBI MongoDB could not be read, so the current access token is unknown."
                ) from error
        if document is None:
            return None
        return stored_login.StoredLogin.from_document(document)

    def api_credentials(self) -> tuple[str, str]:
        """Reads the api key and secret UBI checks connects against.

        Returns:
            A tuple (api_key, api_secret) of str.

        Raises:
            ValueError: The settings document is missing, or has no key or secret.
            UnreachableError: MongoDB could not be read.
        """
        try:
            document = self._find_application_document(SETTINGS_COLLECTION)
        except pymongo.errors.PyMongoError as error:
            raise exceptions.UnreachableError(
                f"UBI MongoDB could not be read for the api key and secret: {error}"
            ) from error
        if document is None:
            raise ValueError(
                f"No settings document for {APPLICATION_NAME} in UBI MongoDB."
            )
        api_key = document.get("api_key")
        api_secret = document.get("api_secret")
        if not api_key or not api_secret:
            raise ValueError(
                f"The {APPLICATION_NAME} settings document has no api_key or api_secret."
            )
        return str(api_key), str(api_secret)

    def close(self) -> None:
        """Closes the connections to both stores.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._redis_client.close()
        self._mongo_client.close()

    def _redis_login(self) -> dict | None:
        """Reads the login document from Redis, treating a failure or unreadable JSON as no document.

        Returns:
            The login dict, or None when Redis has none, cannot be read, or holds text that is not a JSON object.

        Raises:
            Nothing.
        """
        try:
            text = self._redis_client.hget(LOGIN_HASH, APPLICATION_NAME)
        except (redis.RedisError, OSError) as error:
            LOGGER.warning("Could not read the UBI login from Redis: %s", error)
            return None
        if text is None:
            return None
        try:
            document = json.loads(text)
        except json.JSONDecodeError as error:
            LOGGER.warning("The UBI login in Redis is not valid JSON: %s", error)
            return None
        if not isinstance(document, dict):
            return None
        return document

    def _find_application_document(self, collection_name: str) -> dict | None:
        """Finds UBI's own document in one MongoDB collection.

        Args:
            collection_name: The str collection, `last_login` or `settings`.

        Returns:
            The dict document without its `_id`, or None when there is none.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be read.
        """
        collection = self._mongo_client[self._mongo_database_name][collection_name]
        return collection.find_one(
            {
                "broker_name": APPLICATION_NAME,
            },
            {
                "_id": 0,
            },
        )
