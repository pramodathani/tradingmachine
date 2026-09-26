"""A thin REST client for the Unified Broker Interface.

The client asks its token source for an access token, sends every request with that token over one reused connection pool, asks the source again once when the token is refused, and raises a class from `tradingmachine.ubi_client.exceptions` for every failed response. The default token source exchanges the api key and secret from this project's MongoDB for a token; see `tradingmachine.ubi_client.token_sources` for the others.

A client may be shared between threads: token lookups and reconnects happen one at a time under a lock, and requests themselves run in parallel.

Typical usage example:

  unified_broker_interface = client.UnifiedBrokerInterface()
  brokers = unified_broker_interface.get("/api/brokers/details")
  unified_broker_interface.patch("/api/some/route", body={"field": "value"})
"""

import threading
from typing import Any

import requests
import requests.adapters

from tradingmachine.ubi_client import exceptions
from tradingmachine.ubi_client import token_sources
from tradingmachine.utilities import configuration

DEFAULT_TIMEOUT_SECONDS = 30

DEFAULT_CONNECTION_POOL_SIZE = 10

SETTINGS_BROKER_NAME = token_sources.SETTINGS_BROKER_NAME


class UnifiedBrokerInterface:
    """A connection to the Unified Broker Interface REST API.

    Attributes:
        token_expires_at: The str time at which the current access token expires, as reported by the server or by UBI's stored login, or None before the first token is known.
        placement_mode: The str placement mode UBI was last seen using, `engine` or `direct`, or None while it is not known; `tradingmachine.assets.instruments.TradeableInstrument.place_order` sets it.
        token_source: The token_sources.TokenSource the client asks for access tokens.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        project_configuration: configuration.Configuration | None = None,
        token_source: token_sources.TokenSource | None = None,
        connection_pool_size: int = DEFAULT_CONNECTION_POOL_SIZE,
    ):
        """Initialises the client, reading its api key and secret from MongoDB unless a token source is given.

        A configuration is built, and so the environment and the `.env` file read, only when base_url or token_source is missing.

        Args:
            base_url: The str address of the server, such as `http://127.0.0.1:8080`, or None to use `TRADINGMACHINE_UBI_BASE_URL`.
            timeout_seconds: The float number of seconds to wait for each response.
            project_configuration: The configuration.Configuration to read the base url and the MongoDB settings from, or None to build one that reads the environment and the `.env` file when it is needed.
            token_source: The token_sources.TokenSource to ask for access tokens, or None for a token_sources.MongoCredentialTokenSource over the configuration's MongoDB.
            connection_pool_size: The int number of connections to UBI kept open for reuse, which is also how many requests can run at once from different threads without waiting for a connection.

        Raises:
            ValueError: No base url is configured, or, without a token source, the MongoDB settings document or its api key or secret is missing.
        """
        needs_configuration = not base_url or token_source is None
        if project_configuration is None and needs_configuration:
            project_configuration = configuration.Configuration()
        self._configuration = project_configuration
        chosen_base_url = base_url
        if not chosen_base_url:
            chosen_base_url = self._configuration.ubi_base_url
        if not chosen_base_url:
            raise ValueError(
                "UBI base url is not configured: TRADINGMACHINE_UBI_BASE_URL"
            )
        self._base_url = chosen_base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self.token_expires_at = None
        self.placement_mode = None
        if token_source is None:
            token_source = token_sources.MongoCredentialTokenSource(self._configuration)
        self.token_source = token_source
        self._token_lock = threading.RLock()
        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=1,
            pool_maxsize=connection_pool_size,
        )
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def __enter__(self) -> "UnifiedBrokerInterface":
        """Returns the client for a `with` block, which closes it at the end.

        Returns:
            This UnifiedBrokerInterface.

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
        """Closes the pooled connections to UBI.

        The client can still be used afterwards; it opens new connections as needed.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._session.close()

    def connect(self) -> str:
        """Asks the token source to connect to UBI for an access token.

        With the default source this exchanges the api key and secret for a token. UBI hands back the token already in force when it was issued since the most recent 07:00, and otherwise replaces it, which ends any other client's session.

        Returns:
            The access token as a str.

        Raises:
            AuthenticationError: The server refused the api key or secret, or the source may not connect.
            UnifiedBrokerInterfaceError: Any other failure, including an unreachable server.
        """
        with self._token_lock:
            return self.token_source.connect(self)

    def exchange_credentials(self, api_key: str, api_secret: str) -> str:
        """Exchanges an api key and secret for an access token, which is what token sources call to connect.

        Args:
            api_key: The str api key UBI has in its `settings`.
            api_secret: The str api secret UBI has in its `settings`.

        Returns:
            The access token as a str.

        Raises:
            AuthenticationError: The server refused the api key or secret.
            ServerError: The server answered without an access token.
            UnifiedBrokerInterfaceError: Any other failure, including an unreachable server.
        """
        headers = {
            "api-key": api_key,
            "api-secret": api_secret,
        }
        response = self._send(
            "POST",
            "/api/session/connect",
            headers,
            None,
            None,
        )
        response_body = self._parse_body(response)
        if not response.ok:
            self._raise_for_failure(response, response_body)
        if not isinstance(response_body, dict) or not response_body.get("access-token"):
            raise exceptions.ServerError(
                "UBI answered the connect without an access token",
                status_code=response.status_code,
                detail=response_body,
            )
        self.token_expires_at = response_body.get("expires_at")
        return response_body["access-token"]

    def disconnect(self) -> dict:
        """Revokes the access token in force on the server.

        Returns:
            The server's response as a dict, such as `{"status": "disconnected"}`.

        Raises:
            UnifiedBrokerInterfaceError: The server reported a failure or could not be reached.
        """
        response_body = self._request("DELETE", "/api/session/disconnect")
        with self._token_lock:
            self.token_source.forget()
        self.token_expires_at = None
        return response_body

    @property
    def greeting(self) -> dict:
        """UBI's welcome message from `GET /api/`, the one route that needs no access token, as a dict."""
        response = self._send("GET", "/api/", {}, None, None)
        response_body = self._parse_body(response)
        if not response.ok:
            self._raise_for_failure(response, response_body)
        return response_body

    def status(self) -> dict:
        """Reports whether the session is connected and when its token expires.

        Returns:
            The server's response as a dict, such as `{"status": "connected", "expires_at": "..."}`.

        Raises:
            UnifiedBrokerInterfaceError: The server reported a failure or could not be reached.
        """
        return self._request("GET", "/api/session/status")

    def get(self, path: str, params: dict | None = None) -> Any:
        """Sends a GET request.

        Args:
            path: The str route, starting with `/api/`.
            params: A dict of query string parameters, or None.

        Returns:
            The parsed JSON response body, of any JSON type, or None when the body is not JSON.

        Raises:
            UnifiedBrokerInterfaceError: The server reported a failure or could not be reached.
        """
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        body: Any = None,
        params: dict | None = None,
        timeout_seconds: float | None = None,
    ) -> Any:
        """Sends a POST request.

        Args:
            path: The str route, starting with `/api/`.
            body: The request body, of any JSON-serialisable type, or None for no body.
            params: A dict of query string parameters, or None.
            timeout_seconds: The float number of seconds to wait for this one response, or None to use the client's own timeout.

        Returns:
            The parsed JSON response body, of any JSON type, or None when the body is not JSON.

        Raises:
            UnifiedBrokerInterfaceError: The server reported a failure or could not be reached.
        """
        return self._request(
            "POST",
            path,
            params=params,
            body=body,
            timeout_seconds=timeout_seconds,
        )

    def put(
        self,
        path: str,
        body: Any = None,
        params: dict | None = None,
    ) -> Any:
        """Sends a PUT request.

        Args:
            path: The str route, starting with `/api/`.
            body: The request body, of any JSON-serialisable type, or None for no body.
            params: A dict of query string parameters, or None.

        Returns:
            The parsed JSON response body, of any JSON type, or None when the body is not JSON.

        Raises:
            UnifiedBrokerInterfaceError: The server reported a failure or could not be reached.
        """
        return self._request("PUT", path, params=params, body=body)

    def patch(
        self,
        path: str,
        body: Any = None,
        params: dict | None = None,
    ) -> Any:
        """Sends a PATCH request.

        Args:
            path: The str route, starting with `/api/`.
            body: The request body, of any JSON-serialisable type, or None for no body.
            params: A dict of query string parameters, or None.

        Returns:
            The parsed JSON response body, of any JSON type, or None when the body is not JSON.

        Raises:
            UnifiedBrokerInterfaceError: The server reported a failure or could not be reached.
        """
        return self._request("PATCH", path, params=params, body=body)

    def delete(
        self,
        path: str,
        body: Any = None,
        params: dict | None = None,
    ) -> Any:
        """Sends a DELETE request.

        Args:
            path: The str route, starting with `/api/`.
            body: The request body, of any JSON-serialisable type, or None for no body.
            params: A dict of query string parameters, or None.

        Returns:
            The parsed JSON response body, of any JSON type, or None when the body is not JSON.

        Raises:
            UnifiedBrokerInterfaceError: The server reported a failure or could not be reached.
        """
        return self._request("DELETE", path, params=params, body=body)

    def stream_get(self, path: str, params: dict | None = None) -> requests.Response:
        """Sends an authenticated GET whose body is read as it arrives rather than all at once.

        A refused token is replaced and the request sent once more before anything is returned. The caller must close the returned response, or read it to the end.

        Args:
            path: The str route, starting with `/api/`.
            params: A dict of query string parameters, or None.

        Returns:
            The open requests.Response, whose status is successful and whose body has not been read.

        Raises:
            UnifiedBrokerInterfaceError: The server reported a failure or could not be reached.
        """
        token = self._current_token()
        response = self._send(
            "GET",
            path,
            self._token_headers(token),
            params,
            None,
            stream=True,
        )
        if response.status_code == 401:
            response.close()
            token = self._token_after_refusal(token)
            response = self._send(
                "GET",
                path,
                self._token_headers(token),
                params,
                None,
                stream=True,
            )
        if not response.ok:
            response_body = self._parse_body(response)
            response.close()
            self._raise_for_failure(response, response_body)
        return response

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        body: Any = None,
        timeout_seconds: float | None = None,
    ) -> Any:
        """Sends an authenticated request, asking the token source for a new token once if the token is refused.

        Args:
            method: The str HTTP method, such as `GET` or `PATCH`.
            path: The str route, starting with `/api/`.
            params: A dict of query string parameters, or None.
            body: The request body, of any JSON-serialisable type, or None for no body.
            timeout_seconds: The float number of seconds to wait for the response, or None to use the client's own timeout.

        Returns:
            The parsed JSON response body, of any JSON type, or None when the body is not JSON.

        Raises:
            UnifiedBrokerInterfaceError: The server reported a failure or could not be reached.
        """
        token = self._current_token()
        response = self._send(
            method,
            path,
            self._token_headers(token),
            params,
            body,
            timeout_seconds=timeout_seconds,
        )
        if response.status_code == 401:
            token = self._token_after_refusal(token)
            response = self._send(
                method,
                path,
                self._token_headers(token),
                params,
                body,
                timeout_seconds=timeout_seconds,
            )
        response_body = self._parse_body(response)
        if not response.ok:
            self._raise_for_failure(response, response_body)
        return response_body

    def _current_token(self) -> str:
        """Asks the token source for the token to send, under the token lock.

        Returns:
            The str access token.

        Raises:
            UnifiedBrokerInterfaceError: No token could be found or obtained.
        """
        with self._token_lock:
            return self.token_source.current_token(self)

    def _token_after_refusal(self, refused_token: str) -> str:
        """Asks the token source for a token to retry with, under the token lock.

        Args:
            refused_token: The str token UBI answered HTTP 401 to.

        Returns:
            The str access token to retry with.

        Raises:
            UnifiedBrokerInterfaceError: No token could be found or obtained.
        """
        with self._token_lock:
            return self.token_source.token_after_refusal(self, refused_token)

    @staticmethod
    def _token_headers(token: str) -> dict:
        """Builds the headers that carry an access token.

        Args:
            token: The str access token.

        Returns:
            A dict with the `access-token` header.

        Raises:
            Nothing.
        """
        return {
            "access-token": token,
        }

    def _send(
        self,
        method: str,
        path: str,
        headers: dict,
        params: dict | None,
        body: Any,
        timeout_seconds: float | None = None,
        stream: bool = False,
    ) -> requests.Response:
        """Sends one HTTP request to the server over the pooled connections.

        Args:
            method: The str HTTP method, such as `GET` or `PATCH`.
            path: The str route, starting with `/api/`.
            headers: A dict of request headers.
            params: A dict of query string parameters, or None.
            body: The request body, of any JSON-serialisable type, or None for no body.
            timeout_seconds: The float number of seconds to wait for the response, or None to use the client's own timeout.
            stream: A bool that is True to return before the body is read, so it can be read as it arrives.

        Returns:
            The requests.Response received, whatever its status code.

        Raises:
            UnreachableError: The request failed before a response arrived, such as a refused connection or a timeout.
        """
        url = f"{self._base_url}{path}"
        if timeout_seconds is None:
            timeout_seconds = self._timeout_seconds
        try:
            return self._session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=body,
                timeout=timeout_seconds,
                stream=stream,
            )
        except requests.RequestException as error:
            raise exceptions.UnreachableError(
                f"Could not reach UBI at {url}: {error}"
            ) from error

    @staticmethod
    def _parse_body(response: requests.Response) -> Any:
        """Parses a response body as JSON.

        Args:
            response: The requests.Response to parse.

        Returns:
            The parsed body, of any JSON type, or None when the body is empty or not JSON.

        Raises:
            Nothing.
        """
        try:
            return response.json()
        except ValueError:
            return None

    @staticmethod
    def _raise_for_failure(
        response: requests.Response,
        response_body: Any,
    ) -> None:
        """Raises the exception class that matches a failed response's status code.

        The message is the body's `error` field, or its `status_message` when there is no `error`, which is how UBI's order engine explains a 504, or a generic message naming the status code.

        Args:
            response: The failed requests.Response.
            response_body: The parsed JSON body of the response, of any JSON type, or None.

        Raises:
            UnifiedBrokerInterfaceError: Always, as the subclass for the status code, or ServerError when no subclass matches.
        """
        message = None
        if isinstance(response_body, dict):
            message = response_body.get("error")
            if not message:
                message = response_body.get("status_message")
        if not message:
            message = f"UBI returned HTTP {response.status_code}"
        exception_class = exceptions.EXCEPTION_FOR_STATUS_CODE.get(
            response.status_code,
            exceptions.ServerError,
        )
        raise exception_class(
            message,
            status_code=response.status_code,
            detail=response_body,
        )
