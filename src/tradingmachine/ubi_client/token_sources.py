"""Where a UnifiedBrokerInterface gets its access token from.

UBI holds one access token for the whole application, and a token source decides how a client obtains it. `MongoCredentialTokenSource`, the default, reads UBI's api key and secret from this project's MongoDB and exchanges them for a token. `CredentialTokenSource` does the same with a key and secret the caller supplies. `tradingmachine.ubi_stores.stored_login_token_source.StoredLoginTokenSource` reads the token UBI has already stored and connects only when there is none.

The client calls every method while holding its token lock, so a source never needs a lock of its own.

Typical usage example:

  source = token_sources.CredentialTokenSource(api_key, api_secret)
  unified_broker_interface = client.UnifiedBrokerInterface(base_url, token_source=source)
"""

from typing import TYPE_CHECKING

import pymongo

from tradingmachine.utilities import configuration

if TYPE_CHECKING:
    from tradingmachine.ubi_client import client

SETTINGS_BROKER_NAME = "unified_broker_interface"


class TokenSource:
    """The shared shape of every token source; each method must be provided by a subclass."""

    def current_token(
        self,
        unified_broker_interface: "client.UnifiedBrokerInterface",
    ) -> str:
        """Finds the token to send with the next request.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface asking, which a source may use to connect.

        Returns:
            The str access token.

        Raises:
            NotImplementedError: Always, because only a subclass knows where tokens come from.
        """
        raise NotImplementedError(f"{type(self).__name__} must define current_token")

    def token_after_refusal(
        self,
        unified_broker_interface: "client.UnifiedBrokerInterface",
        refused_token: str,
    ) -> str:
        """Finds a token to retry with after UBI answered HTTP 401 to one.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface asking.
            refused_token: The str token UBI refused.

        Returns:
            The str access token to retry with.

        Raises:
            NotImplementedError: Always, because only a subclass knows where tokens come from.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must define token_after_refusal"
        )

    def connect(
        self,
        unified_broker_interface: "client.UnifiedBrokerInterface",
    ) -> str:
        """Obtains a token by connecting to UBI, when the source is allowed to.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface to connect through.

        Returns:
            The str access token.

        Raises:
            NotImplementedError: Always, because only a subclass knows how it connects.
        """
        raise NotImplementedError(f"{type(self).__name__} must define connect")

    def forget(self) -> None:
        """Drops any token the source remembers, as after a disconnect.

        Returns:
            None.

        Raises:
            NotImplementedError: Always, because only a subclass knows what it remembers.
        """
        raise NotImplementedError(f"{type(self).__name__} must define forget")


class CredentialTokenSource(TokenSource):
    """Exchanges an api key and secret for a token, and remembers it until UBI refuses it.

    Every exchange replaces the token UBI holds only when UBI's own token is older than its most recent 07:00; otherwise UBI hands back the token already in force.
    """

    def __init__(self, api_key: str, api_secret: str):
        """Initialises the source with UBI's api key and secret.

        Args:
            api_key: The str api key UBI has in its `settings`.
            api_secret: The str api secret UBI has in its `settings`.

        Raises:
            ValueError: The key or the secret is empty.
        """
        if not api_key or not api_secret:
            raise ValueError("An api key and an api secret are both required")
        self._api_key = api_key
        self._api_secret = api_secret
        self._token = None

    def current_token(
        self,
        unified_broker_interface: "client.UnifiedBrokerInterface",
    ) -> str:
        """Returns the remembered token, connecting first when there is none.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface to connect through.

        Returns:
            The str access token.

        Raises:
            UnifiedBrokerInterfaceError: Connecting failed.
        """
        if self._token is None:
            return self.connect(unified_broker_interface)
        return self._token

    def token_after_refusal(
        self,
        unified_broker_interface: "client.UnifiedBrokerInterface",
        refused_token: str,
    ) -> str:
        """Connects again, unless another request already replaced the refused token.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface to connect through.
            refused_token: The str token UBI refused.

        Returns:
            The str access token to retry with.

        Raises:
            UnifiedBrokerInterfaceError: Connecting failed.
        """
        if self._token is not None and self._token != refused_token:
            return self._token
        return self.connect(unified_broker_interface)

    def connect(
        self,
        unified_broker_interface: "client.UnifiedBrokerInterface",
    ) -> str:
        """Exchanges the key and secret for a token and remembers it.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface to connect through.

        Returns:
            The str access token.

        Raises:
            AuthenticationError: UBI refused the key or secret.
            UnifiedBrokerInterfaceError: Any other failure, including an unreachable server.
        """
        self._token = unified_broker_interface.exchange_credentials(
            self._api_key,
            self._api_secret,
        )
        return self._token

    def forget(self) -> None:
        """Drops the remembered token, so the next request connects.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._token = None


class MongoCredentialTokenSource(CredentialTokenSource):
    """A CredentialTokenSource whose key and secret come from this project's MongoDB.

    The pair is read once, when the source is created, from the `settings` document whose `broker_name` is `unified_broker_interface`.
    """

    def __init__(self, project_configuration: configuration.Configuration):
        """Reads the api key and secret from MongoDB.

        Args:
            project_configuration: The configuration.Configuration that names the MongoDB database and holds its connection string.

        Raises:
            ValueError: The settings document is missing, or it has no api key or no api secret.
        """
        api_key, api_secret = self._read_credentials(project_configuration)
        super().__init__(api_key, api_secret)

    @staticmethod
    def _read_credentials(
        project_configuration: configuration.Configuration,
    ) -> tuple[str, str]:
        """Reads the api key and secret from the project's MongoDB `settings` collection.

        Args:
            project_configuration: The configuration.Configuration that names the MongoDB database.

        Returns:
            A tuple (api_key, api_secret) of str.

        Raises:
            ValueError: The settings document is missing, or it has no api key or no api secret.
        """
        database_name = project_configuration.mongodb_database_name
        with pymongo.MongoClient(
            project_configuration.mongodb_connection_string
        ) as mongo_client:
            settings = mongo_client[database_name]["settings"].find_one(
                {
                    "broker_name": SETTINGS_BROKER_NAME,
                }
            )
        if settings is None:
            raise ValueError(
                f"No settings document with broker_name={SETTINGS_BROKER_NAME!r} in MongoDB database {database_name!r}"
            )
        api_key = settings.get("api_key")
        api_secret = settings.get("api_secret")
        if not api_key or not api_secret:
            raise ValueError(
                f"Settings document {SETTINGS_BROKER_NAME!r} is missing api_key or api_secret"
            )
        return api_key, api_secret
