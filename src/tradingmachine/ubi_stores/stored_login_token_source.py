"""A token source that uses the access token UBI has already stored, and connects only when there is none.

UBI holds one access token for the whole application. A connect made after the most recent 07:00 hands back that same token, but the first connect after 07:00 replaces it and ends every other client's session. This source avoids connecting whenever it can: it reads the token UBI stores in its Redis (or its MongoDB), uses it while it has more than `expiry_margin_seconds` left, and after a refusal first looks for a newer stored token that another client obtained. Only when there is no usable token does it connect, if it is allowed to and has not tried within `connect_cooldown_seconds`.

Typical usage example:

  source = StoredLoginTokenSource(reader, clock.SystemClock(), may_connect=True)
  unified_broker_interface = client.UnifiedBrokerInterface(base_url, token_source=source)
"""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from tradingmachine.ubi_client import exceptions
from tradingmachine.ubi_client import token_sources
from tradingmachine.ubi_stores import stored_login
from tradingmachine.ubi_stores import stored_login_reader
from tradingmachine.utilities import clock

if TYPE_CHECKING:
    from tradingmachine.ubi_client import client

LOGGER = logging.getLogger(__name__)


class StoredLoginTokenSource(token_sources.TokenSource):
    """Uses UBI's stored access token, connecting only as a last resort.

    Attributes:
        may_connect: A bool that is False to never connect, raising AuthenticationError instead.
        connect_cooldown_seconds: The float shortest time between two connect attempts, in seconds.
        expiry_margin_seconds: The float time a stored token must still be valid for to be used, in seconds.
        connect_count: The int number of successful connects this source has made.
        connect_listener: A callable taking one str message, called after each successful connect, or None.
    """

    def __init__(
        self,
        reader: stored_login_reader.StoredLoginReader,
        time_source: clock.SystemClock,
        may_connect: bool = True,
        connect_cooldown_seconds: float = 60.0,
        expiry_margin_seconds: float = 30.0,
    ):
        """Initialises the source.

        Args:
            reader: The stored_login_reader.StoredLoginReader for UBI's stores.
            time_source: The clock.SystemClock, or any object with a `now` method, that gives the current time.
            may_connect: A bool that is True when this process may call UBI's connect route.
            connect_cooldown_seconds: The float shortest time between two connect attempts, in seconds.
            expiry_margin_seconds: The float time a stored token must still be valid for to be used, in seconds.

        Raises:
            Nothing.
        """
        self.may_connect = may_connect
        self.connect_cooldown_seconds = connect_cooldown_seconds
        self.expiry_margin_seconds = expiry_margin_seconds
        self.connect_count = 0
        self.connect_listener: Callable[[str], None] | None = None
        self._reader = reader
        self._time_source = time_source
        self._last_connect_attempt_at = None

    def current_token(
        self,
        unified_broker_interface: "client.UnifiedBrokerInterface",
    ) -> str:
        """Returns UBI's stored token when it is usable, and otherwise connects.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface asking, whose token_expires_at is set to the stored expiry.

        Returns:
            The str access token.

        Raises:
            AuthenticationError: No usable token is stored and connecting is not allowed, is cooling down, or was refused.
            UnreachableError: Neither Redis nor MongoDB could be read, or UBI could not be reached to connect.
            ServerError: UBI answered the connect without a token.
            ValueError: UBI's api key or secret is missing from its MongoDB.
        """
        token = self._usable_stored_token(unified_broker_interface, None)
        if token is not None:
            return token
        return self.connect(unified_broker_interface)

    def token_after_refusal(
        self,
        unified_broker_interface: "client.UnifiedBrokerInterface",
        refused_token: str,
    ) -> str:
        """Returns a newer stored token when another client has connected since, and otherwise connects.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface asking.
            refused_token: The str token UBI answered HTTP 401 to.

        Returns:
            The str access token to retry with.

        Raises:
            AuthenticationError: No newer token is stored and connecting is not allowed, is cooling down, or was refused.
            UnreachableError: Neither Redis nor MongoDB could be read, or UBI could not be reached to connect.
            ServerError: UBI answered the connect without a token.
            ValueError: UBI's api key or secret is missing from its MongoDB.
        """
        token = self._usable_stored_token(unified_broker_interface, refused_token)
        if token is not None:
            return token
        return self.connect(unified_broker_interface)

    def connect(
        self,
        unified_broker_interface: "client.UnifiedBrokerInterface",
    ) -> str:
        """Exchanges UBI's own api key and secret for a token, if this source may and is not cooling down.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface to connect through.

        Returns:
            The str access token.

        Raises:
            AuthenticationError: Connecting is not allowed, is cooling down, or was refused.
            UnreachableError: UBI or its MongoDB could not be reached.
            ServerError: UBI answered without a token.
            ValueError: UBI's api key or secret is missing from its MongoDB.
        """
        if not self.may_connect:
            raise exceptions.AuthenticationError(
                "UBI has no usable access token stored, and this process is not allowed to connect for one."
            )
        now = self._time_source.now()
        if self._last_connect_attempt_at is not None:
            elapsed = now - self._last_connect_attempt_at
            if elapsed < self.connect_cooldown_seconds:
                raise exceptions.AuthenticationError(
                    f"UBI refused the access token again {elapsed:.0f} seconds after the last connect; this process waits {self.connect_cooldown_seconds:.0f} seconds between connects."
                )
        self._last_connect_attempt_at = now
        api_key, api_secret = self._reader.api_credentials()
        token = unified_broker_interface.exchange_credentials(api_key, api_secret)
        self.connect_count += 1
        expires_at = unified_broker_interface.token_expires_at
        if self.connect_listener is not None:
            self.connect_listener(
                f"Connected to UBI for an access token expiring {expires_at}; if UBI issued a new one, other UBI clients were logged out."
            )
        LOGGER.warning(
            "Connected to UBI for an access token expiring %s; if UBI issued a new one, other UBI clients were logged out.",
            expires_at,
        )
        return token

    def forget(self) -> None:
        """Does nothing, because the token belongs to UBI's stores rather than to this source.

        Returns:
            None.

        Raises:
            Nothing.
        """

    def stored_login(self) -> stored_login.StoredLogin | None:
        """Reads UBI's stored login, for a status page or health check.

        Returns:
            The stored_login.StoredLogin, or None when neither store has one.

        Raises:
            UnreachableError: Redis had no readable login and MongoDB could not be read.
        """
        return self._reader.stored_login()

    def _usable_stored_token(
        self,
        unified_broker_interface: "client.UnifiedBrokerInterface",
        excluded_token: str | None,
    ) -> str | None:
        """Finds the stored token when it is usable and is not the excluded one.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface whose token_expires_at is set when a token is found.
            excluded_token: The str token known to be refused, or None.

        Returns:
            The str stored token, or None when there is no usable one.

        Raises:
            UnreachableError: Neither Redis nor MongoDB could be read.
        """
        login = self._reader.stored_login()
        if login is None:
            return None
        if not login.is_usable(self._time_source.now(), self.expiry_margin_seconds):
            return None
        if login.access_token == excluded_token:
            return None
        unified_broker_interface.token_expires_at = login.expires_at_text
        return login.access_token
