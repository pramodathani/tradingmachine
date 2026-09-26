"""Tests for token sources, connection reuse, the greeting and streamed requests."""

import threading

import pytest

from tests import fake_ubi_server
from tests import fakes
from tradingmachine.ubi_client import client
from tradingmachine.ubi_client import exceptions
from tradingmachine.ubi_client import token_sources
from tradingmachine.utilities import configuration


class RefusingTokenSource(token_sources.TokenSource):
    """A token source that fails the test if the client ever asks it for a token."""

    def current_token(
        self, unified_broker_interface: client.UnifiedBrokerInterface
    ) -> str:
        """Fails, because the caller should not have needed a token.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface asking.

        Returns:
            Never returns.

        Raises:
            AssertionError: Always.
        """
        raise AssertionError("The token source was asked for a token")


class ConfigurationTrap:
    """A replacement for configuration.Configuration that fails the test if it is ever built."""

    def __init__(self, *arguments: object, **keyword_arguments: object):
        """Fails, because the client should not have built a configuration.

        Args:
            *arguments: Any positional arguments.
            **keyword_arguments: Any keyword arguments.

        Raises:
            AssertionError: Always.
        """
        raise AssertionError("A Configuration was built")


class TestCredentialTokenSource:
    """A client given a CredentialTokenSource needs neither MongoDB nor a configuration."""

    def test_injected_source_needs_no_configuration(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
    ) -> None:
        """Checks that neither MongoDB nor a configuration is touched.

        Args:
            monkeypatch: The pytest.MonkeyPatch for this test.
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB, which must stay unused.

        Raises:
            AssertionError: MongoDB or a configuration was used, or the request failed.
        """
        monkeypatch.setattr(configuration, "Configuration", ConfigurationTrap)
        ubi_server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
        source = token_sources.CredentialTokenSource(
            fake_ubi_server.API_KEY,
            fake_ubi_server.API_SECRET,
        )
        unified_broker_interface = client.UnifiedBrokerInterface(
            base_url=ubi_server.base_url,
            token_source=source,
        )
        assert unified_broker_interface.get("/api/brokers/details") == {"brokers": []}
        assert mongo_factory.clients == []
        assert unified_broker_interface.token_source is source

    def test_empty_key_is_refused(self) -> None:
        """Checks that a missing key or secret fails at once.

        Raises:
            AssertionError: No ValueError was raised.
        """
        with pytest.raises(ValueError):
            token_sources.CredentialTokenSource("", "secret")
        with pytest.raises(ValueError):
            token_sources.CredentialTokenSource("key", "")

    def test_concurrent_refusals_connect_once(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that eight threads refused at once share one new token.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: More than one new token was issued, or a request failed.
        """
        ubi_server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
        unified_broker_interface = client.UnifiedBrokerInterface(
            base_url=ubi_server.base_url,
            token_source=token_sources.CredentialTokenSource(
                fake_ubi_server.API_KEY,
                fake_ubi_server.API_SECRET,
            ),
        )
        unified_broker_interface.get("/api/brokers/details")
        ubi_server.refuse_all_tokens()
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
        for _ in range(8):
            threads.append(threading.Thread(target=ask))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert failures == []
        assert ubi_server.issued_tokens == ["token-1", "token-2"]

    def test_connect_without_token_raises_server_error(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks a connect answer that carries no token.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: No ServerError was raised.
        """
        ubi_server.connect_answer = fake_ubi_server.PreparedAnswer(
            200, {"status": "ok"}
        )
        unified_broker_interface = client.UnifiedBrokerInterface(
            base_url=ubi_server.base_url,
            token_source=token_sources.CredentialTokenSource(
                fake_ubi_server.API_KEY,
                fake_ubi_server.API_SECRET,
            ),
        )
        with pytest.raises(exceptions.ServerError, match="without an access token"):
            unified_broker_interface.connect()


class TestTransport:
    """Connections are reused, the greeting needs no token, and bodies can be streamed."""

    def test_requests_reuse_one_connection(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that sequential requests arrive over the same connection.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The requests came from different client ports.
        """
        ubi_server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
        with client.UnifiedBrokerInterface(
            base_url=ubi_server.base_url,
            token_source=token_sources.CredentialTokenSource(
                fake_ubi_server.API_KEY,
                fake_ubi_server.API_SECRET,
            ),
        ) as unified_broker_interface:
            for _ in range(3):
                unified_broker_interface.get("/api/brokers/details")
        ports = set()
        for request in ubi_server.requests:
            ports.add(request.client_port)
        assert len(ports) == 1

    def test_client_works_after_close(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that closing only drops the pooled connections.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The request after close failed.
        """
        ubi_server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
        unified_broker_interface = client.UnifiedBrokerInterface(
            base_url=ubi_server.base_url,
            token_source=token_sources.CredentialTokenSource(
                fake_ubi_server.API_KEY,
                fake_ubi_server.API_SECRET,
            ),
        )
        unified_broker_interface.get("/api/brokers/details")
        unified_broker_interface.close()
        assert unified_broker_interface.get("/api/brokers/details") == {"brokers": []}

    def test_greeting_needs_no_token(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that the greeting never asks the token source.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The token source was asked, or the greeting was wrong.
        """
        welcome = {
            "message": "Welcome to the Unified Broker Interface API",
        }
        ubi_server.answer("GET", "/api/", 200, welcome)
        unified_broker_interface = client.UnifiedBrokerInterface(
            base_url=ubi_server.base_url,
            token_source=RefusingTokenSource(),
        )
        assert unified_broker_interface.greeting == welcome

    def test_greeting_failure_raises(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that a failed greeting raises like any other request.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: No ServerError was raised.
        """
        ubi_server.answer("GET", "/api/", 500, {"error": "down"})
        unified_broker_interface = client.UnifiedBrokerInterface(
            base_url=ubi_server.base_url,
            token_source=RefusingTokenSource(),
        )
        with pytest.raises(exceptions.ServerError, match="down"):
            unified_broker_interface.greeting

    def test_stream_get_retries_a_refused_token(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that a streamed request is retried after a 401 and returned open.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The stream was not retried or its body was wrong.
        """
        ubi_server.answer(
            "GET",
            "/api/instruments/master",
            200,
            chunks=[
                b"[1,",
                b"2]",
            ],
        )
        ubi_server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
        unified_broker_interface = client.UnifiedBrokerInterface(
            base_url=ubi_server.base_url,
            token_source=token_sources.CredentialTokenSource(
                fake_ubi_server.API_KEY,
                fake_ubi_server.API_SECRET,
            ),
        )
        unified_broker_interface.get("/api/brokers/details")
        ubi_server.refuse_all_tokens()
        response = unified_broker_interface.stream_get(
            "/api/instruments/master",
            params={"exchange": "all"},
        )
        with response:
            content = b"".join(response.iter_content(chunk_size=None))
        assert content == b"[1,2]"
        assert ubi_server.issued_tokens == ["token-1", "token-2"]
        assert ubi_server.requests_to("/api/instruments/master")[-1].query == {
            "exchange": "all"
        }

    def test_stream_get_raises_for_a_failure(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
    ) -> None:
        """Checks that a failed streamed request raises the class for its status.

        Args:
            ubi_server: The running fake UBI server.

        Raises:
            AssertionError: The wrong exception was raised.
        """
        ubi_server.answer(
            "GET", "/api/instruments/master", 400, {"error": "bad segment"}
        )
        unified_broker_interface = client.UnifiedBrokerInterface(
            base_url=ubi_server.base_url,
            token_source=token_sources.CredentialTokenSource(
                fake_ubi_server.API_KEY,
                fake_ubi_server.API_SECRET,
            ),
        )
        with pytest.raises(exceptions.BadRequestError, match="bad segment"):
            unified_broker_interface.stream_get("/api/instruments/master")
