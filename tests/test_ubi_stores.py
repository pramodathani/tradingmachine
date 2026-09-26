"""Tests for reading UBI's stored login, its live quotes, and the token source built on the stored login."""

import datetime
import inspect
import re
import threading

import pymongo
import pytest
import redis

from tests import fake_ubi_server
from tests import fakes
from tradingmachine.ubi_client import client
from tradingmachine.ubi_client import exceptions
from tradingmachine.ubi_stores import live_quote_reader
from tradingmachine.ubi_stores import store_settings
from tradingmachine.ubi_stores import stored_login
from tradingmachine.ubi_stores import stored_login_reader
from tradingmachine.ubi_stores import stored_login_token_source

UBI_DATABASE = "unified_broker_interface"

START = datetime.datetime(2026, 9, 16, 10, 0, 0).timestamp()  # noqa: DTZ001

TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

REDIS_SETTINGS = store_settings.RedisSettings(
    host="127.0.0.1",
    port=1002,
    database=0,
    username="default",
    password="redis-password",
    timeout_seconds=5.0,
)

MONGO_SETTINGS = store_settings.MongoSettings(
    host="127.0.0.1",
    port=1003,
    database_name=UBI_DATABASE,
    username="root",
    password="mongo-password",
    timeout_seconds=5.0,
)


class UbiStores:
    """UBI's Redis and MongoDB, faked, with helpers to fill them.

    Attributes:
        redis_factory: The fakes.FakeRedisFactory standing in for redis.Redis.
        mongo_factory: The fakes.FakeMongoClientFactory standing in for pymongo.MongoClient.
        clock: The fakes.FixedClock the token source reads.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch):
        """Replaces redis.Redis and pymongo.MongoClient with fakes holding UBI's settings.

        Args:
            monkeypatch: The pytest.MonkeyPatch for this test.

        Raises:
            Nothing.
        """
        self.redis_factory = fakes.FakeRedisFactory()
        self.mongo_factory = fakes.FakeMongoClientFactory(
            fakes.SettingsDatabase.with_credentials(UBI_DATABASE)
        )
        self.mongo_factory.databases[UBI_DATABASE]["last_login"] = fakes.FakeCollection(
            []
        )
        self.clock = fakes.FixedClock(START)
        monkeypatch.setattr(redis, "Redis", self.redis_factory)
        monkeypatch.setattr(pymongo, "MongoClient", self.mongo_factory)

    def expiry(self, seconds: float) -> str:
        """Writes an expiry some seconds from the clock's time, in UBI's format.

        Args:
            seconds: The float number of seconds ahead.

        Returns:
            The str expiry in local time.

        Raises:
            Nothing.
        """
        moment = datetime.datetime.fromtimestamp(self.clock.now() + seconds)  # noqa: DTZ006
        return moment.strftime(TIME_FORMAT)

    def store_redis_login(self, token: str, seconds: float) -> None:
        """Stores a login in UBI's Redis.

        Args:
            token: The str token.
            seconds: The float number of seconds until it expires.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.redis_factory.store_json(
            "last_login",
            "unified_broker_interface",
            {
                "broker_name": "unified_broker_interface",
                "access_token": token,
                "expires_at": self.expiry(seconds),
            },
        )

    def store_mongo_login(self, token: str, seconds: float) -> None:
        """Stores a login in UBI's MongoDB.

        Args:
            token: The str token.
            seconds: The float number of seconds until it expires.

        Returns:
            None.

        Raises:
            Nothing.
        """
        collection = self.mongo_factory.databases[UBI_DATABASE]["last_login"]
        collection.documents.append(
            {
                "_id": "login-document",
                "broker_name": "unified_broker_interface",
                "access_token": token,
                "expires_at": self.expiry(seconds),
            }
        )

    def fail_mongo(self) -> None:
        """Makes every MongoDB read fail.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for collection in self.mongo_factory.databases[UBI_DATABASE].values():
            collection.failing = True

    def credential_reads(self) -> int:
        """Counts the reads of UBI's settings collection.

        Returns:
            The int number of find_one calls on `settings`.

        Raises:
            Nothing.
        """
        return len(self.mongo_factory.databases[UBI_DATABASE]["settings"].queries)


@pytest.fixture
def stores(monkeypatch: pytest.MonkeyPatch) -> UbiStores:
    """Fakes UBI's Redis and MongoDB for one test.

    Args:
        monkeypatch: The pytest.MonkeyPatch for this test.

    Returns:
        The UbiStores.

    Raises:
        Nothing.
    """
    return UbiStores(monkeypatch)


def build_source(
    stores: UbiStores,
    ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    may_connect: bool = True,
) -> tuple[
    stored_login_token_source.StoredLoginTokenSource,
    client.UnifiedBrokerInterface,
]:
    """Builds a stored-login token source and a client using it; UBI's connect route stores each new token in the fake Redis, as UBI does.

    Args:
        stores: The faked UBI stores.
        ubi_server: The running fake UBI server.
        may_connect: A bool that is True when the source may connect.

    Returns:
        A tuple (source, unified_broker_interface) of the StoredLoginTokenSource and the client.UnifiedBrokerInterface.

    Raises:
        Nothing.
    """

    def store_new_token(token: str, expires_at: str) -> None:
        """Stores a token the fake server issued in the fake Redis.

        Args:
            token: The str new token.
            expires_at: The str expiry.

        Returns:
            None.

        Raises:
            Nothing.
        """
        stores.redis_factory.store_json(
            "last_login",
            "unified_broker_interface",
            {
                "access_token": token,
                "expires_at": expires_at,
            },
        )

    ubi_server.connect_listener = store_new_token
    reader = stored_login_reader.StoredLoginReader(REDIS_SETTINGS, MONGO_SETTINGS)
    source = stored_login_token_source.StoredLoginTokenSource(
        reader,
        stores.clock,
        may_connect=may_connect,
        connect_cooldown_seconds=60.0,
        expiry_margin_seconds=30.0,
    )
    unified_broker_interface = client.UnifiedBrokerInterface(
        base_url=ubi_server.base_url,
        token_source=source,
    )
    return source, unified_broker_interface


class TestStoredLogin:
    """StoredLogin reads UBI's login documents and decides whether a token is usable."""

    def test_stored_document_is_read(self) -> None:
        """Checks that the token and a local-time expiry with microseconds are read.

        Raises:
            AssertionError: A field was read wrongly.
        """
        login = stored_login.StoredLogin.from_document(
            {
                "broker_name": "unified_broker_interface",
                "access_token": "abc",
                "last_login": "2026-09-15 16:24:15.239134",
                "expires_at": "2026-09-16 16:24:15.239134",
            }
        )
        expected = datetime.datetime(2026, 9, 16, 16, 24, 15, 239134).timestamp()  # noqa: DTZ001
        assert login.access_token == "abc"
        assert login.expires_at_epoch == expected

    def test_connect_answer_is_read(self) -> None:
        """Checks that the connect answer's hyphenated token key is read.

        Raises:
            AssertionError: The token was not read.
        """
        login = stored_login.StoredLogin.from_document(
            {
                "access-token": "xyz",
                "expires_at": "2026-09-16 11:00:00.000000",
            }
        )
        assert login.access_token == "xyz"
        assert login.is_usable(START, 30.0)

    def test_token_close_to_expiry_is_not_usable(self) -> None:
        """Checks that a token expiring within the margin is not used.

        Raises:
            AssertionError: The margin was not respected.
        """
        login = stored_login.StoredLogin("abc", "2026-09-16 10:00:20.000000")
        assert not login.is_usable(START, 30.0)
        assert login.is_usable(START, 10.0)

    def test_disconnected_or_unreadable_login_is_not_usable(self) -> None:
        """Checks UBI's disconnected document and an expiry in an unknown format.

        Raises:
            AssertionError: Either was treated as usable.
        """
        disconnected = stored_login.StoredLogin.from_document(
            {
                "access_token": None,
                "expires_at": None,
            }
        )
        unreadable = stored_login.StoredLogin("abc", "tomorrow")
        assert not disconnected.is_usable(START, 30.0)
        assert unreadable.expires_at_epoch is None
        assert not unreadable.is_usable(START, 30.0)

    def test_description_hides_the_token(self) -> None:
        """Checks that printing a login never shows the token.

        Raises:
            AssertionError: The token appeared.
        """
        login = stored_login.StoredLogin(
            "secret-token-value", "2026-09-16 16:24:15.239134"
        )
        assert "secret-token-value" not in repr(login)
        assert "has_token=True" in repr(login)


class TestStoredLoginReader:
    """StoredLoginReader reads Redis first, MongoDB second, and UBI's key and secret."""

    def test_clients_are_built_from_the_settings(self, stores: UbiStores) -> None:
        """Checks the connection options given to Redis and MongoDB.

        Args:
            stores: The faked UBI stores.

        Raises:
            AssertionError: An option was wrong.
        """
        stored_login_reader.StoredLoginReader(REDIS_SETTINGS, MONGO_SETTINGS)
        redis_options = stores.redis_factory.clients[0].keyword_arguments
        assert redis_options["port"] == 1002
        assert redis_options["password"] == "redis-password"
        assert redis_options["decode_responses"] is True
        assert redis_options["socket_timeout"] == 5.0
        mongo_options = stores.mongo_factory.clients[0].keyword_arguments
        assert mongo_options["port"] == 1003
        assert mongo_options["serverSelectionTimeoutMS"] == 5000
        assert "secret" not in repr(REDIS_SETTINGS) + repr(MONGO_SETTINGS)

    def test_bad_json_in_redis_falls_back_to_mongodb(self, stores: UbiStores) -> None:
        """Checks that an unreadable Redis value is treated as missing.

        Args:
            stores: The faked UBI stores.

        Raises:
            AssertionError: The MongoDB login was not used.
        """
        stores.redis_factory.hashes["last_login"] = {
            "unified_broker_interface": "{not json",
        }
        stores.store_mongo_login("from-mongo", 3600)
        reader = stored_login_reader.StoredLoginReader(REDIS_SETTINGS, MONGO_SETTINGS)
        assert reader.stored_login().access_token == "from-mongo"

    def test_no_login_anywhere_is_none(self, stores: UbiStores) -> None:
        """Checks that empty stores give None.

        Args:
            stores: The faked UBI stores.

        Raises:
            AssertionError: Something other than None was returned.
        """
        del stores
        reader = stored_login_reader.StoredLoginReader(REDIS_SETTINGS, MONGO_SETTINGS)
        assert reader.stored_login() is None

    def test_api_credentials(self, stores: UbiStores) -> None:
        """Checks the key and secret, and the error for an incomplete settings document.

        Args:
            stores: The faked UBI stores.

        Raises:
            AssertionError: The credentials or the error were wrong.
        """
        reader = stored_login_reader.StoredLoginReader(REDIS_SETTINGS, MONGO_SETTINGS)
        assert reader.api_credentials() == (
            fake_ubi_server.API_KEY,
            fake_ubi_server.API_SECRET,
        )
        settings = stores.mongo_factory.databases[UBI_DATABASE]["settings"]
        del settings.documents[0]["api_secret"]
        with pytest.raises(ValueError, match="no api_key or api_secret"):
            reader.api_credentials()
        settings.documents.clear()
        with pytest.raises(ValueError, match="No settings document"):
            reader.api_credentials()

    def test_close_closes_both_clients(self, stores: UbiStores) -> None:
        """Checks that closing reaches Redis and MongoDB.

        Args:
            stores: The faked UBI stores.

        Raises:
            AssertionError: A client stayed open.
        """
        reader = stored_login_reader.StoredLoginReader(REDIS_SETTINGS, MONGO_SETTINGS)
        reader.close()
        assert stores.redis_factory.clients[0].closed
        assert stores.mongo_factory.clients[0].closed


class TestStoredLoginTokenSource:
    """StoredLoginTokenSource uses UBI's stored token and connects only as a last resort."""

    def test_usable_stored_token_is_used_without_connecting(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that a valid token in Redis is sent and nothing connects.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The source connected or sent another token.
        """
        stores.store_redis_login("stored", 3600)
        ubi_server.valid_tokens.add("stored")
        ubi_server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
        source, unified_broker_interface = build_source(stores, ubi_server)
        assert unified_broker_interface.get("/api/brokers/details") == {"brokers": []}
        assert (
            ubi_server.requests_to("/api/brokers/details")[0].headers["access-token"]
            == "stored"
        )
        assert ubi_server.requests_to("/api/session/connect") == []
        assert source.connect_count == 0
        assert unified_broker_interface.token_expires_at == stores.expiry(3600)

    def test_token_near_expiry_leads_to_a_connect(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that a token expiring within the margin is replaced by connecting with UBI's own key and secret, and the listener hears of it.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The source did not connect as expected.
        """
        stores.store_redis_login("stale", 10)
        source, unified_broker_interface = build_source(stores, ubi_server)
        descriptions = []
        source.connect_listener = descriptions.append
        assert unified_broker_interface.connect() == "token-1"
        assert len(descriptions) == 1
        assert "other UBI clients were logged out" in descriptions[0]
        request = ubi_server.requests_to("/api/session/connect")[0]
        assert request.headers["api-key"] == fake_ubi_server.API_KEY
        assert source.connect_count == 1

    def test_mongodb_login_is_used_when_redis_has_none(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that the MongoDB copy of the login is used when Redis has no field.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The MongoDB token was not used.
        """
        stores.store_mongo_login("from-mongo", 3600)
        source, unified_broker_interface = build_source(stores, ubi_server)
        assert source.current_token(unified_broker_interface) == "from-mongo"
        assert ubi_server.requests_to("/api/session/connect") == []

    def test_redis_failure_falls_back_to_mongodb(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that an unreachable Redis does not stop the MongoDB copy being used.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The MongoDB token was not used.
        """
        stores.store_redis_login("from-redis", 3600)
        stores.store_mongo_login("from-mongo", 3600)
        source, unified_broker_interface = build_source(stores, ubi_server)
        stores.redis_factory.set_failing(True)
        assert source.current_token(unified_broker_interface) == "from-mongo"

    def test_unreadable_stores_never_lead_to_a_connect(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that when neither store can be read, the source refuses rather than connecting blindly.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: No UnreachableError was raised, or the source connected.
        """
        source, unified_broker_interface = build_source(stores, ubi_server)
        stores.redis_factory.set_failing(True)
        stores.fail_mongo()
        with pytest.raises(exceptions.UnreachableError):
            source.current_token(unified_broker_interface)
        assert ubi_server.requests_to("/api/session/connect") == []

    def test_refusal_with_a_newer_stored_token_does_not_connect(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that after a 401, a token another client obtained is adopted without connecting.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The newer token was not adopted.
        """
        stores.store_redis_login("old", 3600)
        source, unified_broker_interface = build_source(stores, ubi_server)
        refused = source.current_token(unified_broker_interface)
        stores.store_redis_login("tradingmachine", 86400)
        assert source.token_after_refusal(unified_broker_interface, refused) == (
            "tradingmachine"
        )
        assert ubi_server.requests_to("/api/session/connect") == []

    def test_refusal_of_the_stored_token_connects_once(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that when UBI refuses the token it still stores, a request connects once and succeeds.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The request did not connect exactly once.
        """
        stores.store_redis_login("revoked", 3600)
        ubi_server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
        source, unified_broker_interface = build_source(stores, ubi_server)
        assert unified_broker_interface.get("/api/brokers/details") == {"brokers": []}
        assert ubi_server.issued_tokens == ["token-1"]
        assert source.connect_count == 1

    def test_second_refusal_within_the_cooldown_does_not_connect(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that two refusals within a minute lead to one connect and then an error.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The cooldown was not respected.
        """
        stores.store_redis_login("revoked", 3600)
        source, unified_broker_interface = build_source(stores, ubi_server)
        new_token = source.token_after_refusal(unified_broker_interface, "revoked")
        stores.clock.advance(20)
        with pytest.raises(exceptions.AuthenticationError, match="waits 60"):
            source.token_after_refusal(unified_broker_interface, new_token)
        assert len(ubi_server.requests_to("/api/session/connect")) == 1

    def test_connect_is_allowed_again_after_the_cooldown(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that a connect is allowed once the cooldown has passed.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The second connect was refused.
        """
        stores.store_redis_login("revoked", 3600)
        source, unified_broker_interface = build_source(stores, ubi_server)
        new_token = source.token_after_refusal(unified_broker_interface, "revoked")
        stores.clock.advance(61)
        source.token_after_refusal(unified_broker_interface, new_token)
        assert len(ubi_server.requests_to("/api/session/connect")) == 2

    def test_process_that_may_not_connect_raises(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that a source without permission to connect never connects or reads the key and secret.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The source connected or read the credentials.
        """
        source, unified_broker_interface = build_source(
            stores, ubi_server, may_connect=False
        )
        with pytest.raises(exceptions.AuthenticationError, match="not allowed"):
            source.current_token(unified_broker_interface)
        assert ubi_server.requests_to("/api/session/connect") == []
        assert stores.credential_reads() == 0

    def test_refused_connect_raises_authentication_error(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that a connect refused by UBI raises AuthenticationError with UBI's message.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: No AuthenticationError was raised.
        """
        source, unified_broker_interface = build_source(stores, ubi_server)
        ubi_server.connect_answer = fake_ubi_server.PreparedAnswer(
            401, {"error": "Invalid API key or secret"}
        )
        with pytest.raises(exceptions.AuthenticationError, match="Invalid API key"):
            source.current_token(unified_broker_interface)

    def test_concurrent_requests_share_one_connect(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that requests arriving together without a stored token cause only one connect.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: More than one connect happened, or a request failed.
        """
        ubi_server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
        source, unified_broker_interface = build_source(stores, ubi_server)
        failures = []

        def ask() -> None:
            """Sends one request, recording any failure.

            Returns:
                None.

            Raises:
                Nothing.
            """
            try:
                unified_broker_interface.get("/api/brokers/details")
            except exceptions.UnifiedBrokerInterfaceError as error:
                failures.append(error)

        threads = []
        for _ in range(6):
            threads.append(threading.Thread(target=ask))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert failures == []
        assert ubi_server.issued_tokens == ["token-1"]
        assert source.connect_count == 1

    def test_stored_login_is_offered_for_health_checks(
        self,
        stores: UbiStores,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks stored_login, and that forget changes nothing.

        Args:
            stores: The faked UBI stores.
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The stored login was wrong.
        """
        stores.store_redis_login("stored", 3600)
        source, _ = build_source(stores, ubi_server)
        source.forget()
        assert source.stored_login().access_token == "stored"


class TestLiveQuoteReader:
    """LiveQuoteReader reads the live quotes hash in batches."""

    def test_quotes_are_read_in_batches(self, stores: UbiStores) -> None:
        """Checks batching, repeated ids, missing quotes and values that are not JSON objects.

        Args:
            stores: The faked UBI stores.

        Raises:
            AssertionError: A quote or a batch was wrong.
        """
        for index in range(5):
            stores.redis_factory.store_json(
                "unified:quotes:live",
                f"id-{index}",
                {"instrument_id": f"id-{index}", "last_price": index},
            )
        stores.redis_factory.hashes["unified:quotes:live"]["id-3"] = "{broken"
        stores.redis_factory.store_json("unified:quotes:live", "id-4", [1, 2])
        reader = live_quote_reader.LiveQuoteReader(REDIS_SETTINGS, batch_size=2)
        quotes = reader.read(
            ["id-0", "id-1", "id-0", "id-2", "id-3", "id-4", "missing"]
        )
        assert list(quotes) == ["id-0", "id-1", "id-2"]
        assert quotes["id-2"]["last_price"] == 2
        batches = []
        for command, name, fields in stores.redis_factory.clients[0].commands:
            assert command == "hmget"
            assert name == "unified:quotes:live"
            batches.append(fields)
        assert batches == [
            ["id-0", "id-1"],
            ["id-2", "id-3"],
            ["id-4", "missing"],
        ]

    def test_no_ids_sends_nothing(self, stores: UbiStores) -> None:
        """Checks that an empty list reads nothing.

        Args:
            stores: The faked UBI stores.

        Raises:
            AssertionError: A command was sent.
        """
        reader = live_quote_reader.LiveQuoteReader(REDIS_SETTINGS)
        assert reader.read([]) == {}
        assert stores.redis_factory.clients[0].commands == []

    def test_redis_failure_raises_unreachable_error(self, stores: UbiStores) -> None:
        """Checks that a Redis failure becomes UnreachableError.

        Args:
            stores: The faked UBI stores.

        Raises:
            AssertionError: No UnreachableError was raised.
        """
        reader = live_quote_reader.LiveQuoteReader(REDIS_SETTINGS)
        stores.redis_factory.set_failing(True)
        with pytest.raises(exceptions.UnreachableError):
            reader.read(["id-0"])

    def test_batch_size_must_be_positive(self, stores: UbiStores) -> None:
        """Checks that a batch size of zero is refused.

        Args:
            stores: The faked UBI stores.

        Raises:
            AssertionError: No ValueError was raised.
        """
        del stores
        with pytest.raises(ValueError):
            live_quote_reader.LiveQuoteReader(REDIS_SETTINGS, batch_size=0)


class TestReadOnly:
    """The store readers can only read, which protects UBI's stores from this library."""

    WRITE_CALL = re.compile(
        r"\.(set|hset|hmset|hdel|delete|del|expire|lpush|rpush|xadd|publish|"
        r"insert_one|insert_many|update_one|update_many|replace_one|"
        r"delete_one|delete_many|find_one_and_\w+|bulk_write|drop|"
        r"create_index)\("
    )

    @pytest.mark.parametrize(
        ("reader_class", "allowed"),
        [
            (
                stored_login_reader.StoredLoginReader,
                {
                    "stored_login",
                    "api_credentials",
                    "close",
                },
            ),
            (
                live_quote_reader.LiveQuoteReader,
                {
                    "read",
                    "close",
                },
            ),
        ],
    )
    def test_public_methods_only_read(self, reader_class: type, allowed: set) -> None:
        """Checks that each reader offers no public method beyond its reads and close.

        Args:
            reader_class: The reader class.
            allowed: A set of the str public method names allowed.

        Raises:
            AssertionError: A public method was added.
        """
        public = set()
        for name, member in inspect.getmembers(reader_class, inspect.isfunction):
            if not name.startswith("_"):
                public.add(name)
        assert public == allowed

    @pytest.mark.parametrize(
        "module",
        [
            stored_login_reader,
            live_quote_reader,
            stored_login_token_source,
        ],
    )
    def test_source_has_no_write_calls(self, module: object) -> None:
        """Checks that no Redis or MongoDB write command appears in the stores' source.

        Args:
            module: The module to scan.

        Raises:
            AssertionError: A write call was found.
        """
        source = inspect.getsource(module)
        assert self.WRITE_CALL.findall(source) == []
