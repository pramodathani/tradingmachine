# tests/fake_ubi_server.py

The test suite was added on 2026-09-26, when instruments_explorer started using tradingmachine for all of its UBI access and tradingmachine gained read-only market data classes for it. The first tests pin down how `UnifiedBrokerInterface` behaved before that work began (`tests/test_client.py`), so the refactor that followed could be checked against them.

## Why a real HTTP server rather than a patched `requests`

The client was about to move from `requests.request` to a shared `requests.Session`, and to gain a streaming download. Tests that patched `requests.request` would have stopped intercepting anything after the first change, and could not exercise chunked streaming at all. A small `http.server.ThreadingHTTPServer` on a free local port receives real requests whatever the client uses underneath, so the same tests prove the behaviour before and after.

## How it imitates UBI

- `POST /api/session/connect` issues `token-1`, `token-2` and so on when the `api-key` and `api-secret` headers match `API_KEY` and `API_SECRET`, and answers 401 otherwise. `connect_answer` replaces that answer for tests of odd connect replies.
- Every other route except the greeting at `/api/` answers 401 `{"error": "Invalid access token"}` unless the `access-token` header is a token it issued and has not since refused. `refuse_all_tokens` imitates an expired or rotated token.
- Answers are prepared per method and path with `answer`. A body of any JSON type is sent as JSON; a `str` is sent as HTML, which imitates Flask's error pages; `chunks` sends a list of byte strings with chunked transfer encoding, which imitates UBI's streamed instrument master.
- Every request is recorded as a `RecordedRequest`, with lower-case header names, so tests can check which token was sent.

`serve_forever` polls for shutdown every 0.05 seconds rather than the default 0.5, which took the suite from 12 seconds to about 1.

The request handler class is defined inside `start` so that it can close over the server object; `http.server` builds a new handler instance per request and gives it no other way to reach shared state.
