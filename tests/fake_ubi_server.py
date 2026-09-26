"""A small HTTP server that stands in for the Unified Broker Interface in tests.

The server runs on a free local port in a background thread, so the client under test sends real HTTP requests and every transport detail, such as connection reuse and streaming, is exercised. It issues access tokens from its own connect route, refuses unknown tokens with HTTP 401 as UBI does, and answers every other route from answers the test prepares.

Typical usage example:

  with fake_ubi_server.FakeUnifiedBrokerInterfaceServer() as server:
      server.answer("GET", "/api/brokers/details", 200, {"brokers": []})
      unified_broker_interface = client.UnifiedBrokerInterface(base_url=server.base_url, ...)
"""

import http.server
import json
import threading
import urllib.parse
from typing import Any

API_KEY = "test-api-key"
API_SECRET = "test-api-secret"


class RecordedRequest:
    """One request the fake server received.

    Attributes:
        method: The str HTTP method.
        path: The str path without the query string.
        query: A dict of the query string, with one str value per name.
        headers: A dict of the request headers, with lower-case str names.
        body: The parsed JSON body, of any JSON type, or None when there was none.
        client_port: The int local port the request came from, which stays the same while a connection is reused.
    """

    def __init__(
        self,
        method: str,
        path: str,
        query: dict,
        headers: dict,
        body: Any,
        client_port: int,
    ):
        """Initialises the record.

        Args:
            method: The str HTTP method.
            path: The str path without the query string.
            query: A dict of the query string, with one str value per name.
            headers: A dict of the request headers, with lower-case str names.
            body: The parsed JSON body, of any JSON type, or None.
            client_port: The int local port the request came from.

        Raises:
            Nothing.
        """
        self.method = method
        self.path = path
        self.query = query
        self.headers = headers
        self.body = body
        self.client_port = client_port


class PreparedAnswer:
    """An answer the fake server gives to one route.

    Attributes:
        status_code: The int HTTP status code.
        body: The body, of any JSON type, sent as JSON, or a str or bytes sent as it is.
        headers: A dict of extra response headers.
        chunks: A list of bytes sent one after another with chunked encoding in place of the body, or None.
    """

    def __init__(
        self,
        status_code: int,
        body: Any = None,
        headers: dict | None = None,
        chunks: list[bytes] | None = None,
    ):
        """Initialises the answer.

        Args:
            status_code: The int HTTP status code.
            body: The body, of any JSON type, or a str or bytes sent as it is.
            headers: A dict of extra response headers, or None.
            chunks: A list of bytes to stream in place of the body, or None.

        Raises:
            Nothing.
        """
        self.status_code = status_code
        self.body = body
        if headers is None:
            headers = {}
        self.headers = headers
        self.chunks = chunks


class FakeUnifiedBrokerInterfaceServer:
    """A running stand-in for UBI's REST API.

    Attributes:
        requests: A list of RecordedRequest, one per request received, in order.
        issued_tokens: A list of the str tokens the connect route has issued, in order.
        valid_tokens: A set of the str tokens currently accepted.
        connect_answer: A PreparedAnswer that replaces the normal connect answer, or None.
    """

    def __init__(self):
        """Initialises the server without starting it.

        Raises:
            Nothing.
        """
        self.requests = []
        self.issued_tokens = []
        self._lock = threading.Lock()
        self.valid_tokens = set()
        self.connect_answer = None
        self._answers = {}
        self._http_server = None
        self._thread = None

    @property
    def base_url(self) -> str:
        """The str address of the running server, such as `http://127.0.0.1:40123`."""
        host, port = self._http_server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> None:
        """Starts serving on a free local port in a background thread.

        Returns:
            None.

        Raises:
            OSError: No local port could be opened.
        """
        server = self

        class Handler(_FakeRequestHandler):
            """The request handler bound to this server."""

            fake_server = server

        self._http_server = http.server.ThreadingHTTPServer(
            (
                "127.0.0.1",
                0,
            ),
            Handler,
        )
        self._thread = threading.Thread(
            target=self._http_server.serve_forever,
            kwargs={
                "poll_interval": 0.05,
            },
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stops the server and waits for its thread.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._http_server.shutdown()
        self._http_server.server_close()
        self._thread.join()

    def __enter__(self) -> "FakeUnifiedBrokerInterfaceServer":
        """Starts the server for a `with` block.

        Returns:
            The started FakeUnifiedBrokerInterfaceServer.

        Raises:
            OSError: No local port could be opened.
        """
        self.start()
        return self

    def __exit__(self, *exception_information: Any) -> None:
        """Stops the server at the end of a `with` block.

        Args:
            *exception_information: The exception type, value and traceback, or three Nones.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.stop()

    def answer(
        self,
        method: str,
        path: str,
        status_code: int,
        body: Any = None,
        headers: dict | None = None,
        chunks: list[bytes] | None = None,
    ) -> None:
        """Prepares the answer for one route, replacing any earlier one.

        Args:
            method: The str HTTP method, such as `GET`.
            path: The str path, such as `/api/instruments/details`.
            status_code: The int HTTP status code.
            body: The body, of any JSON type, or a str or bytes sent as it is.
            headers: A dict of extra response headers, or None.
            chunks: A list of bytes to stream in place of the body, or None.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._answers[(method, path)] = PreparedAnswer(
            status_code,
            body,
            headers,
            chunks,
        )

    def refuse_all_tokens(self) -> None:
        """Makes every token issued so far invalid, as when UBI's token expires.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.valid_tokens.clear()

    def requests_to(self, path: str) -> list[RecordedRequest]:
        """Lists the requests received for one path.

        Args:
            path: The str path.

        Returns:
            A list of RecordedRequest, in order.

        Raises:
            Nothing.
        """
        matching = []
        for request in self.requests:
            if request.path == path:
                matching.append(request)
        return matching

    def handle(self, request: RecordedRequest) -> PreparedAnswer:
        """Chooses the answer to one request.

        Args:
            request: The RecordedRequest received.

        Returns:
            The PreparedAnswer to send.

        Raises:
            Nothing.
        """
        with self._lock:
            self.requests.append(request)
            if request.method == "POST" and request.path == "/api/session/connect":
                return self._connect(request)
        if request.path != "/api/":
            token = request.headers.get("access-token")
            if token not in self.valid_tokens:
                return PreparedAnswer(
                    401,
                    {
                        "error": "Invalid access token",
                    },
                )
        prepared = self._answers.get((request.method, request.path))
        if prepared is None:
            return PreparedAnswer(
                404,
                {
                    "error": f"No prepared answer for {request.method} {request.path}",
                },
            )
        return prepared

    def _connect(self, request: RecordedRequest) -> PreparedAnswer:
        """Answers the connect route, issuing a new token when the key and secret match.

        Args:
            request: The RecordedRequest for the connect route.

        Returns:
            The PreparedAnswer to send.

        Raises:
            Nothing.
        """
        if self.connect_answer is not None:
            return self.connect_answer
        if (
            request.headers.get("api-key") != API_KEY
            or request.headers.get("api-secret") != API_SECRET
        ):
            return PreparedAnswer(
                401,
                {
                    "error": "Invalid api key or secret",
                },
            )
        token = f"token-{len(self.issued_tokens) + 1}"
        self.issued_tokens.append(token)
        self.valid_tokens.add(token)
        return PreparedAnswer(
            200,
            {
                "access-token": token,
                "expires_at": "2099-01-01 07:00:00.000000",
            },
        )


class _FakeRequestHandler(http.server.BaseHTTPRequestHandler):
    """Turns each HTTP request into a RecordedRequest and writes the chosen answer."""

    fake_server = None
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        """Handles a GET request.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._handle()

    def do_POST(self) -> None:  # noqa: N802
        """Handles a POST request.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._handle()

    def do_PUT(self) -> None:  # noqa: N802
        """Handles a PUT request.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._handle()

    def do_PATCH(self) -> None:  # noqa: N802
        """Handles a PATCH request.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._handle()

    def do_DELETE(self) -> None:  # noqa: N802
        """Handles a DELETE request.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self._handle()

    def log_message(self, format: str, *arguments: Any) -> None:  # noqa: A002
        """Keeps the test output quiet.

        Args:
            format: The str log format.
            *arguments: The values for the format.

        Returns:
            None.

        Raises:
            Nothing.
        """
        del format, arguments

    def _handle(self) -> None:
        """Records the request, then writes the chosen answer.

        Returns:
            None.

        Raises:
            Nothing.
        """
        address = urllib.parse.urlsplit(self.path)
        query = {}
        for name, value in urllib.parse.parse_qsl(address.query):
            query[name] = value
        headers = {}
        for name, value in self.headers.items():
            headers[name.lower()] = value
        body = None
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            body = json.loads(self.rfile.read(length))
        request = RecordedRequest(
            self.command,
            address.path,
            query,
            headers,
            body,
            self.client_address[1],
        )
        prepared = self.fake_server.handle(request)
        self._write(prepared)

    def _write(self, prepared: PreparedAnswer) -> None:
        """Writes one answer, whole or in chunks.

        Args:
            prepared: The PreparedAnswer to write.

        Returns:
            None.

        Raises:
            Nothing.
        """
        self.send_response(prepared.status_code)
        for name, value in prepared.headers.items():
            self.send_header(name, value)
        if prepared.chunks is not None:
            self.send_header("Content-Type", "application/json")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for chunk in prepared.chunks:
                self.wfile.write(f"{len(chunk):x}\r\n".encode())
                self.wfile.write(chunk)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            return
        if isinstance(prepared.body, bytes):
            content = prepared.body
            content_type = "application/octet-stream"
        elif isinstance(prepared.body, str):
            content = prepared.body.encode()
            content_type = "text/html"
        elif prepared.body is None:
            content = b""
            content_type = "application/json"
        else:
            content = json.dumps(prepared.body).encode()
            content_type = "application/json"
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
