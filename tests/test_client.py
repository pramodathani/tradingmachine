"""Tests that pin down how UnifiedBrokerInterface authenticates, retries and reports failures."""

import pytest

from tests import fake_ubi_server
from tests import fakes
from tradingmachine.ubi_client import client
from tradingmachine.ubi_client import exceptions
from tradingmachine.utilities import configuration


class TestDefaultAuthentication:
    """The default client reads the api key and secret from MongoDB and connects on first use."""

    def test_first_request_connects_with_key_and_secret(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks that the first request connects once and sends the issued token.

        Args:
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: The client did not connect as expected.
        """
        ubi_server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
        unified_broker_interface = client.UnifiedBrokerInterface(
            project_configuration=project_configuration
        )
        answer = unified_broker_interface.get("/api/brokers/details")
        assert answer == {"brokers": []}
        assert ubi_server.issued_tokens == ["token-1"]
        request = ubi_server.requests_to("/api/brokers/details")[0]
        assert request.headers["access-token"] == "token-1"
        assert unified_broker_interface.token_expires_at == "2099-01-01 07:00:00.000000"
        assert mongo_factory.clients[0].closed

    def test_later_requests_reuse_the_token(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks that a second request does not connect again.

        Args:
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: The client connected more than once.
        """
        del mongo_factory
        ubi_server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
        unified_broker_interface = client.UnifiedBrokerInterface(
            project_configuration=project_configuration
        )
        unified_broker_interface.get("/api/brokers/details")
        unified_broker_interface.get("/api/brokers/details")
        assert ubi_server.issued_tokens == ["token-1"]

    def test_refused_token_reconnects_once(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks that a 401 leads to one new connect and a retry with the new token.

        Args:
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: The client did not reconnect and retry.
        """
        del mongo_factory
        ubi_server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
        unified_broker_interface = client.UnifiedBrokerInterface(
            project_configuration=project_configuration
        )
        unified_broker_interface.get("/api/brokers/details")
        ubi_server.refuse_all_tokens()
        answer = unified_broker_interface.get("/api/brokers/details")
        assert answer == {"brokers": []}
        assert ubi_server.issued_tokens == ["token-1", "token-2"]
        tokens_sent = []
        for request in ubi_server.requests_to("/api/brokers/details"):
            tokens_sent.append(request.headers["access-token"])
        assert tokens_sent == ["token-1", "token-1", "token-2"]

    def test_second_refusal_raises_authentication_error(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks that a route refusing every token raises rather than looping.

        Args:
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: The client did not raise AuthenticationError.
        """
        del mongo_factory
        ubi_server.answer(
            "GET", "/api/brokers/details", 401, {"error": "Access token has expired"}
        )
        unified_broker_interface = client.UnifiedBrokerInterface(
            project_configuration=project_configuration
        )
        with pytest.raises(exceptions.AuthenticationError) as raised:
            unified_broker_interface.get("/api/brokers/details")
        assert raised.value.message == "Access token has expired"
        assert len(ubi_server.issued_tokens) == 2

    def test_wrong_secret_raises_authentication_error(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks that a refused connect is raised without retrying.

        Args:
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: The client did not raise AuthenticationError.
        """
        settings = mongo_factory.databases["tradingmachine_test"]["settings"]
        settings.documents[0]["api_secret"] = "wrong"
        unified_broker_interface = client.UnifiedBrokerInterface(
            project_configuration=project_configuration
        )
        with pytest.raises(exceptions.AuthenticationError):
            unified_broker_interface.connect()
        assert len(ubi_server.requests_to("/api/session/connect")) == 1

    def test_missing_settings_document_raises_value_error(
        self,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks that construction fails when MongoDB has no key and secret.

        Args:
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: The client did not raise ValueError.
        """
        mongo_factory.databases["tradingmachine_test"]["settings"].documents.clear()
        with pytest.raises(ValueError, match="No settings document"):
            client.UnifiedBrokerInterface(project_configuration=project_configuration)

    def test_missing_base_url_raises_value_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks that construction fails without a base url.

        Args:
            monkeypatch: The pytest.MonkeyPatch for this test.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: The client did not raise ValueError.
        """
        del mongo_factory
        monkeypatch.delenv(configuration.UBI_BASE_URL_VARIABLE)
        with pytest.raises(ValueError, match="base url"):
            client.UnifiedBrokerInterface(project_configuration=project_configuration)


class TestFailures:
    """Failed responses become one exception class per status code."""

    @pytest.mark.parametrize(
        ("status_code", "exception_class"),
        [
            (400, exceptions.BadRequestError),
            (403, exceptions.LossLockoutError),
            (404, exceptions.NotFoundError),
            (409, exceptions.ConflictError),
            (422, exceptions.OrderRejectedError),
            (429, exceptions.RateLimitError),
            (500, exceptions.ServerError),
            (502, exceptions.BrokerError),
            (503, exceptions.ServiceUnavailableError),
            (504, exceptions.OrderOutcomeUnknownError),
            (405, exceptions.ServerError),
        ],
    )
    def test_status_code_chooses_the_class(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
        status_code: int,
        exception_class: type,
    ) -> None:
        """Checks the class, message, status code and detail of one failure.

        Args:
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.
            status_code: The int status code the route answers with.
            exception_class: The exception class expected.

        Raises:
            AssertionError: The wrong class or fields were raised.
        """
        del mongo_factory
        body = {
            "error": f"failure {status_code}",
        }
        ubi_server.answer("GET", "/api/some/route", status_code, body)
        unified_broker_interface = client.UnifiedBrokerInterface(
            project_configuration=project_configuration
        )
        with pytest.raises(exception_class) as raised:
            unified_broker_interface.get("/api/some/route")
        assert type(raised.value) is exception_class
        assert raised.value.message == f"failure {status_code}"
        assert raised.value.status_code == status_code
        assert raised.value.detail == body

    def test_message_falls_back_to_status_message(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks the order engine's 504, which explains itself in status_message.

        Args:
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: The message was not taken from status_message.
        """
        del mongo_factory
        ubi_server.answer(
            "POST",
            "/api/orders/place",
            504,
            {"status_message": "the engine did not answer in time"},
        )
        unified_broker_interface = client.UnifiedBrokerInterface(
            project_configuration=project_configuration
        )
        with pytest.raises(exceptions.OrderOutcomeUnknownError) as raised:
            unified_broker_interface.post("/api/orders/place", body={})
        assert raised.value.message == "the engine did not answer in time"

    def test_message_falls_back_to_the_status_code(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks a failure whose body is not JSON, such as Flask's HTML error page.

        Args:
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: The generic message or empty detail was wrong.
        """
        del mongo_factory
        ubi_server.answer("GET", "/api/some/route", 500, "<html>boom</html>")
        unified_broker_interface = client.UnifiedBrokerInterface(
            project_configuration=project_configuration
        )
        with pytest.raises(exceptions.ServerError) as raised:
            unified_broker_interface.get("/api/some/route")
        assert raised.value.message == "UBI returned HTTP 500"
        assert raised.value.detail == {}

    def test_non_json_success_returns_none(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks that a successful answer that is not JSON is returned as None.

        Args:
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: Something other than None was returned.
        """
        del mongo_factory
        ubi_server.answer("GET", "/api/some/route", 200, "not json")
        unified_broker_interface = client.UnifiedBrokerInterface(
            project_configuration=project_configuration
        )
        assert unified_broker_interface.get("/api/some/route") is None

    def test_closed_port_raises_unreachable_error(
        self,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks that a refused connection becomes UnreachableError.

        Args:
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: The client did not raise UnreachableError.
        """
        del mongo_factory
        unified_broker_interface = client.UnifiedBrokerInterface(
            base_url="http://127.0.0.1:9",
            timeout_seconds=2,
            project_configuration=project_configuration,
        )
        with pytest.raises(exceptions.UnreachableError) as raised:
            unified_broker_interface.get("/api/some/route")
        assert raised.value.status_code is None


class TestRequests:
    """Each method sends its HTTP method, parameters and body."""

    def test_methods_send_parameters_and_body(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks GET, POST, PUT, PATCH and DELETE.

        Args:
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: A request was sent differently.
        """
        del mongo_factory
        for method in [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ]:
            ubi_server.answer(method, "/api/thing", 200, {"method": method})
        unified_broker_interface = client.UnifiedBrokerInterface(
            project_configuration=project_configuration
        )
        assert unified_broker_interface.get("/api/thing", params={"a": "1"}) == {
            "method": "GET"
        }
        unified_broker_interface.post("/api/thing", body={"b": 2}, params={"c": "3"})
        unified_broker_interface.put("/api/thing", body={"d": 4})
        unified_broker_interface.patch("/api/thing", body={"e": 5})
        unified_broker_interface.delete("/api/thing", body={"f": 6})
        sent = ubi_server.requests_to("/api/thing")
        assert [request.method for request in sent] == [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ]
        assert sent[0].query == {"a": "1"}
        assert sent[1].query == {"c": "3"}
        assert sent[1].body == {"b": 2}
        assert sent[4].body == {"f": 6}

    def test_disconnect_forgets_the_token(
        self,
        ubi_server: fake_ubi_server.FakeUnifiedBrokerInterfaceServer,
        mongo_factory: fakes.FakeMongoClientFactory,
        project_configuration: configuration.Configuration,
    ) -> None:
        """Checks that the request after a disconnect connects again.

        Args:
            ubi_server: The running fake UBI server.
            mongo_factory: The fake MongoDB holding the key and secret.
            project_configuration: A configuration pointing at the fakes.

        Raises:
            AssertionError: The client kept the old token.
        """
        del mongo_factory
        ubi_server.answer(
            "DELETE", "/api/session/disconnect", 200, {"status": "disconnected"}
        )
        ubi_server.answer("GET", "/api/session/status", 200, {"status": "connected"})
        unified_broker_interface = client.UnifiedBrokerInterface(
            project_configuration=project_configuration
        )
        assert unified_broker_interface.status() == {"status": "connected"}
        assert unified_broker_interface.disconnect() == {"status": "disconnected"}
        assert unified_broker_interface.token_expires_at is None
        unified_broker_interface.status()
        assert ubi_server.issued_tokens == ["token-1", "token-2"]
