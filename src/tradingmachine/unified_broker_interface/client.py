"""A thin REST client for the Unified Broker Interface.

The client exchanges the api key and secret for an access token, sends every request with that token, reconnects once when the token is refused, and raises a class from `tradingmachine.unified_broker_interface.exceptions` for every failed response.

Typical usage example:

  unified_broker_interface = client.UnifiedBrokerInterface()
  brokers = unified_broker_interface.get("/api/brokers/details")
  unified_broker_interface.patch("/api/some/route", body={"field": "value"})
"""

from typing import Any

import pymongo
import requests

from tradingmachine.unified_broker_interface import exceptions
from tradingmachine.utilities import configuration

DEFAULT_TIMEOUT_SECONDS = 30

SETTINGS_BROKER_NAME = "unified_broker_interface"


class UnifiedBrokerInterface:
    """A connection to the Unified Broker Interface REST API.

    Attributes:
        token_expires_at: The str time at which the current access token expires, as reported by the server, or None before the first connect.
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

        Examples:
            Connect and report the token's length and expiry without printing the token itself:

            ```python
            from tradingmachine.unified_broker_interface import client

            unified_broker_interface = client.UnifiedBrokerInterface()
            access_token = unified_broker_interface.connect()
            print(f"The token has {len(access_token)} characters.")
            print(f"It expires at {unified_broker_interface.token_expires_at}.")
            ```

            Connect explicitly before the first request, then confirm the session:

            ```python
            from tradingmachine.unified_broker_interface import client

            unified_broker_interface = client.UnifiedBrokerInterface()
            unified_broker_interface.connect()
            print(unified_broker_interface.status())
            ```
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

        Examples:
            Revoke the token and then connect again, so that other clients can reconnect:

            ```python
            from tradingmachine.unified_broker_interface import client

            unified_broker_interface = client.UnifiedBrokerInterface()
            unified_broker_interface.connect()
            print(unified_broker_interface.disconnect())
            unified_broker_interface.connect()
            print(unified_broker_interface.status()["status"])
            ```

            Disconnect inside `try` and always reconnect in `finally`:

            ```python
            from tradingmachine.unified_broker_interface import client

            unified_broker_interface = client.UnifiedBrokerInterface()
            unified_broker_interface.connect()
            try:
                answer = unified_broker_interface.disconnect()
                print(f"UBI answered: {answer['status']}")
                print(f"Token expiry now: {unified_broker_interface.token_expires_at}")
            finally:
                unified_broker_interface.connect()
            ```
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

        Examples:
            Print whether the session is connected and when its token expires:

            ```python
            from tradingmachine.unified_broker_interface import client

            unified_broker_interface = client.UnifiedBrokerInterface()
            print(unified_broker_interface.status())
            ```

            Work out how long the current token has left:

            ```python
            import datetime

            from tradingmachine.unified_broker_interface import client

            unified_broker_interface = client.UnifiedBrokerInterface()
            session = unified_broker_interface.status()
            expires_at = datetime.datetime.fromisoformat(session["expires_at"])
            remaining = expires_at - datetime.datetime.now()
            print(f"{session['status']}, {remaining} left")
            ```
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

        Examples:
            Read the last price of one share with query string parameters:

            ```python
            from tradingmachine.unified_broker_interface import client

            unified_broker_interface = client.UnifiedBrokerInterface()
            answer = unified_broker_interface.get(
                "/api/instruments/ltp",
                params={
                    "exchange": "nse",
                    "segment": "equities",
                    "symbol": "IDEA",
                },
            )
            print(answer["symbol"], answer["last_price"])
            ```

            List the brokers UBI is connected to:

            ```python
            from tradingmachine.unified_broker_interface import client

            unified_broker_interface = client.UnifiedBrokerInterface()
            brokers = unified_broker_interface.get("/api/brokers/details")
            for broker in brokers:
                print(broker["broker_name"])
            ```

            See how fresh each broker's funds are in UBI:

            ```python
            from tradingmachine.unified_broker_interface import client

            unified_broker_interface = client.UnifiedBrokerInterface()
            funds = unified_broker_interface.get("/api/portfolio/funds")
            for broker in funds["brokers"]:
                print(broker["broker"], broker["status"], broker["as_of"])
            ```
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

        Examples:
            Read the last prices of several shares in one list request:

            ```python
            from tradingmachine.unified_broker_interface import client

            unified_broker_interface = client.UnifiedBrokerInterface()
            answer = unified_broker_interface.post(
                "/api/instruments/ltp",
                body={
                    "instruments": [
                        {
                            "exchange": "nse",
                            "segment": "equities",
                            "symbol": "IDEA",
                        },
                        {
                            "exchange": "nse",
                            "segment": "equities",
                            "symbol": "INFY",
                        },
                    ],
                },
            )
            for result in answer["results"]:
                print(result["data"]["symbol"], result["data"]["last_price"])
            ```

            Look up the lot and tick size of two instruments at once, with a longer timeout:

            ```python
            from tradingmachine.unified_broker_interface import client

            unified_broker_interface = client.UnifiedBrokerInterface()
            answer = unified_broker_interface.post(
                "/api/instruments/details",
                body={
                    "instruments": [
                        {
                            "exchange": "nse",
                            "segment": "equities",
                            "symbol": "TCS",
                        },
                        {
                            "exchange": "nse",
                            "segment": "equity_indices",
                            "symbol": "NIFTY",
                        },
                    ],
                },
                timeout_seconds=60,
            )
            for result in answer["results"]:
                details = result["data"]
                print(details["symbol"], details["lot_size"], details["tick_size"])
            ```
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

        Examples:
            Change the price of a held limit order through `PUT /api/orders/modify`, then cancel it:

            ```python
            from tradingmachine.assets import equities

            idea = equities.Equity(exchange="nse", symbol="IDEA")
            price = round(idea.last_price * 0.97, 2)
            answer = idea.buy_at_limit_price(price=price, quantity=1, product="mis")
            try:
                unified_broker_interface = idea.shared_unified_broker_interface()
                changed = unified_broker_interface.put(
                    "/api/orders/modify",
                    body={
                        "parent_id": answer["parent_id"],
                        "price": round(price - 0.05, 2),
                    },
                )
                print(changed["outcome"], changed["price"])
            finally:
                idea.cancel_parent(answer["parent_id"])
            ```

            Handle the error UBI answers for a parent id it does not hold:

            ```python
            from tradingmachine.unified_broker_interface import client
            from tradingmachine.unified_broker_interface import exceptions

            unified_broker_interface = client.UnifiedBrokerInterface()
            try:
                unified_broker_interface.put(
                    "/api/orders/modify",
                    body={
                        "parent_id": "00000000-0000-0000-0000-000000000000",
                        "price": 10.0,
                    },
                )
            except exceptions.NotFoundError as error:
                print(error.status_code, error.message)
            ```
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

        Examples:
            Handle the error for a route that does not take PATCH, since UBI has no PATCH route today:

            ```python
            from tradingmachine.unified_broker_interface import client
            from tradingmachine.unified_broker_interface import exceptions

            unified_broker_interface = client.UnifiedBrokerInterface()
            try:
                unified_broker_interface.patch("/api/session/status")
            except exceptions.UnifiedBrokerInterfaceError as error:
                print(type(error).__name__, error.status_code)
            ```

            Send a body with PATCH and report the status code UBI answers:

            ```python
            from tradingmachine.unified_broker_interface import client
            from tradingmachine.unified_broker_interface import exceptions

            unified_broker_interface = client.UnifiedBrokerInterface()
            try:
                answer = unified_broker_interface.patch(
                    "/api/orders/modify",
                    body={
                        "parent_id": "00000000-0000-0000-0000-000000000000",
                    },
                )
                print(answer)
            except exceptions.UnifiedBrokerInterfaceError as error:
                print(f"UBI answered HTTP {error.status_code}")
            ```
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

        Examples:
            Cancel a held limit order with `DELETE /api/orders/parents`:

            ```python
            from tradingmachine.assets import equities

            idea = equities.Equity(exchange="nse", symbol="IDEA")
            price = round(idea.last_price * 0.97, 2)
            answer = idea.buy_at_limit_price(price=price, quantity=1, product="mis")
            unified_broker_interface = idea.shared_unified_broker_interface()
            cancelled = unified_broker_interface.delete(
                "/api/orders/parents",
                body={
                    "parent_id": answer["parent_id"],
                },
            )
            print(cancelled["synthetic_type"], cancelled["state"])
            ```

            Handle the error for cancelling an order id no broker holds:

            ```python
            from tradingmachine.unified_broker_interface import client
            from tradingmachine.unified_broker_interface import exceptions

            unified_broker_interface = client.UnifiedBrokerInterface()
            try:
                unified_broker_interface.delete(
                    "/api/orders/cancel",
                    body={
                        "order_id": "000000000000",
                        "dry_run": True,
                    },
                )
            except exceptions.NotFoundError as error:
                print(error.status_code, error.message)
            ```
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
    def _skipped_text(response_body: Any) -> str:
        """Describes the brokers a refusal says UBI passed over, and why.

        Args:
            response_body: The parsed JSON body of the response, of any JSON type, or None.

        Returns:
            The str `broker: reason` for each entry of the body's `skipped` list, joined with `; `, or an empty str when there is no such list.

        Raises:
            Nothing.
        """
        if not isinstance(response_body, dict):
            return ""
        skipped = response_body.get("skipped")
        if not isinstance(skipped, list):
            return ""
        parts = []
        for entry in skipped:
            if not isinstance(entry, dict):
                continue
            parts.append(f"{entry.get('broker')}: {entry.get('reason')}")
        return "; ".join(parts)

    @staticmethod
    def _raise_for_failure(
        response: requests.Response,
        response_body: Any,
    ) -> None:
        """Raises the exception class that matches a failed response's status code.

        The message is the body's `error` field, or its `status_message` when there is no `error`, which is how UBI's order engine explains a 504, or a generic message naming the status code. When the body lists the brokers UBI passed over in `skipped`, each broker's reason is added to the message, so a refusal such as `no broker can take this order` says why.

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
        skipped_text = UnifiedBrokerInterface._skipped_text(response_body)
        if skipped_text:
            message = f"{message} ({skipped_text})"
        exception_class = exceptions.EXCEPTION_FOR_STATUS_CODE.get(
            response.status_code,
            exceptions.ServerError,
        )
        raise exception_class(
            message,
            status_code=response.status_code,
            detail=response_body,
        )
