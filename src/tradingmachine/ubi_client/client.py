"""A thin REST client for the Unified Broker Interface.

The client exchanges the api key and secret for an access token, sends every request with that token, reconnects once when the token is refused, and raises a class from `tradingmachine.ubi_client.exceptions` for every failed response.

Typical usage example:

  unified_broker_interface = client.UnifiedBrokerInterface()
  brokers = unified_broker_interface.get("/api/brokers/details")
  unified_broker_interface.patch("/api/some/route", body={"field": "value"})
"""

from typing import Any

import pymongo
import requests

from tradingmachine.ubi_client import exceptions
from tradingmachine.utilities import configuration

DEFAULT_TIMEOUT_SECONDS = 30

SETTINGS_BROKER_NAME = "unified_broker_interface"


class UnifiedBrokerInterface:
    """A connection to the Unified Broker Interface REST API.

    Attributes:
        token_expires_at: The str time at which the current access token expires, as reported by the server, or None before the first connect.
        placement_mode: The str placement mode UBI was last seen using, `engine` or `direct`, or None while it is not known; `tradingmachine.assets.instruments.TradeableInstrument.place_order` sets it.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        project_configuration: configuration.Configuration | None = None,
    ):
        """Initialises the client and reads its api key and secret from MongoDB.

        Args:
            base_url: The str address of the server, such as `http://127.0.0.1:8080`, or None to use `TRADINGMACHINE_UBI_BASE_URL`.
            timeout_seconds: The float number of seconds to wait for each response.
            project_configuration: The configuration.Configuration to read the base url and the MongoDB settings from, or None to build one that reads the environment and the `.env` file.

        Raises:
            ValueError: No base url is configured, or the MongoDB settings document or its api key or secret is missing.
        """
        if project_configuration is None:
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
        self._access_token = None
        self._api_key = None
        self._api_secret = None
        self.token_expires_at = None
        self.placement_mode = None
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Reads the api key and secret from the project's MongoDB `settings` collection.

        Raises:
            ValueError: The settings document is missing, or it has no api key or no api secret.
        """
        database_name = self._configuration.mongodb_database_name
        with pymongo.MongoClient(
            self._configuration.mongodb_connection_string
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
        self._api_key = settings.get("api_key")
        self._api_secret = settings.get("api_secret")
        if not self._api_key or not self._api_secret:
            raise ValueError(
                f"Settings document {SETTINGS_BROKER_NAME!r} is missing api_key or api_secret"
            )

    def connect(self) -> str:
        """Exchanges the api key and secret for a new access token.

        The new token replaces the one in force on the server, which ends any other client's session.

        Returns:
            The new access token as a str.

        Raises:
            AuthenticationError: The server refused the api key or secret.
            UnifiedBrokerInterfaceError: Any other failure, including an unreachable server.
        """
        headers = {
            "api-key": self._api_key,
            "api-secret": self._api_secret,
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
        self._access_token = response_body["access-token"]
        self.token_expires_at = response_body.get("expires_at")
        return self._access_token

    def disconnect(self) -> dict:
        """Revokes the access token in force on the server.

        Returns:
            The server's response as a dict, such as `{"status": "disconnected"}`.

        Raises:
            UnifiedBrokerInterfaceError: The server reported a failure or could not be reached.
        """
        response_body = self._request("DELETE", "/api/session/disconnect")
        self._access_token = None
        self.token_expires_at = None
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

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        body: Any = None,
        is_retry: bool = False,
        timeout_seconds: float | None = None,
    ) -> Any:
        """Sends an authenticated request, reconnecting once if the token is refused.

        Args:
            method: The str HTTP method, such as `GET` or `PATCH`.
            path: The str route, starting with `/api/`.
            params: A dict of query string parameters, or None.
            body: The request body, of any JSON-serialisable type, or None for no body.
            is_retry: A bool that is True when this call is already the retry after a refused token.
            timeout_seconds: The float number of seconds to wait for the response, or None to use the client's own timeout.

        Returns:
            The parsed JSON response body, of any JSON type, or None when the body is not JSON.

        Raises:
            UnifiedBrokerInterfaceError: The server reported a failure or could not be reached.
        """
        if self._access_token is None:
            self.connect()
        headers = {
            "access-token": self._access_token,
        }
        response = self._send(
            method,
            path,
            headers,
            params,
            body,
            timeout_seconds=timeout_seconds,
        )
        response_body = self._parse_body(response)
        if response.status_code == 401 and not is_retry:
            self._access_token = None
            return self._request(
                method,
                path,
                params,
                body,
                is_retry=True,
                timeout_seconds=timeout_seconds,
            )
        if not response.ok:
            self._raise_for_failure(response, response_body)
        return response_body

    def _send(
        self,
        method: str,
        path: str,
        headers: dict,
        params: dict | None,
        body: Any,
        timeout_seconds: float | None = None,
    ) -> requests.Response:
        """Sends one HTTP request to the server.

        Args:
            method: The str HTTP method, such as `GET` or `PATCH`.
            path: The str route, starting with `/api/`.
            headers: A dict of request headers.
            params: A dict of query string parameters, or None.
            body: The request body, of any JSON-serialisable type, or None for no body.
            timeout_seconds: The float number of seconds to wait for the response, or None to use the client's own timeout.

        Returns:
            The requests.Response received, whatever its status code.

        Raises:
            UnreachableError: The request failed before a response arrived, such as a refused connection or a timeout.
        """
        url = f"{self._base_url}{path}"
        if timeout_seconds is None:
            timeout_seconds = self._timeout_seconds
        try:
            return requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=body,
                timeout=timeout_seconds,
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
