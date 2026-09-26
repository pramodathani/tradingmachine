# src/tradingmachine/ubi_client/client.py

This module holds `UnifiedBrokerInterface`, a thin wrapper around the REST API of the sibling project `unified_broker_interface` (UBI). It adds no knowledge of UBI's routes: callers pass the path, such as `/api/orders/place`, and get the parsed JSON back. It was adapted from `src/tradingmachine/ubi_client/client.py` in the old tradingmachine project, kept at `/run/media/pramod/6959D90B1DAD7E59/backup_20260910/pramod/Downloads/tradingmachine-master/`, and it adds a `patch` method.

## How a request flows

```
caller ── get / post / put / patch / delete ──► _request
                                                   │
                  under the token lock ──► token_source.current_token
                                                   │     (the default source connects on first use:
                                                   │      exchange_credentials ── POST /api/session/connect)
                                                   ▼
                                               _send ── the shared requests.Session, access-token header
                                                   │
                                            401? ── under the lock: token_source.token_after_refusal,
                                                   │                then _send once more
                                                   │
                                       failure? ── _raise_for_failure ── exceptions class
                                                   │
                                                   ▼
                                           parsed JSON body
```

This flow was reshaped on 2026-09-26; the section "Token sources, the session and the lock" below says why.

## Authentication

UBI authenticates `POST /api/session/connect` with an `api-key` and `api-secret` header pair, and it returns an `access-token` and an `expires_at` time. Every other route except the greeting at `/api/` requires the `access-token` header.

UBI holds a single token for the whole application, not one per client. Each connect replaces it, so one client connecting ends every other client's session, including UBI's own REST API test page. Tokens also expire, after `UNIFIED_BROKER_INTERFACE_API_TOKEN_TTL_SECONDS` (86400 seconds by default). The old client was written when tokens never expired.

Both facts mean a cached token can be refused at any moment. The client therefore does not check `token_expires_at` before each call; it sends the request, and on a 401 it clears the token, connects again and retries exactly once. A second 401 is raised as `AuthenticationError`, so a wrong key or secret cannot cause a loop. `token_expires_at` is kept as a public attribute for callers who want to show or plan around it.

`connect` itself never retries, because a 401 there means the key or secret is wrong.

Because two clients in the same process, or two processes, would keep replacing each other's token, each reconnect-and-retry costs the other client one extra round trip. That is acceptable for now. If several long-running processes start sharing UBI, a shared client or a shared token cache should replace per-instance tokens.

## Where the api key and secret come from

The pair is read from tradingmachine's own MongoDB, from the `settings` collection document whose `broker_name` is `unified_broker_interface`. This is the same shape UBI's `blueprints/session.py` reads from UBI's own MongoDB, and it is the same place the old project used, rather than an environment variable. The user chose this on 2026-09-14.

```json
{
  "broker_name": "unified_broker_interface",
  "api_key": "<the key UBI has in its own settings>",
  "api_secret": "<the secret UBI has in its own settings>"
}
```

The document was seeded by hand on 2026-09-14 with a one-off upsert. If UBI's key or secret changes, this document must be updated to match. MongoDB is read once, in `__init__`, with the client closed by a `with` block, so no database connection stays open for the life of the object.

## How it finds its settings

`__init__` takes an optional `project_configuration`, a `tradingmachine.utilities.configuration.Configuration`, and builds a plain one when it is not given. That object supplies the base url when `base_url` is not passed, and the database name and connection string that `_load_credentials` uses. It is held on `self._configuration` for the life of the client, so every read goes through the same object.

The parameter is named `project_configuration` rather than `configuration` because the module is imported under that name and a parameter called `configuration` would shadow it inside the method.

Before 2026-09-20 the module read two module-level dictionaries directly, and there was no way to point one client at a different `.env` from another. The parameter was added when those dictionaries became a class, as part of turning the project into an installable library. Passing nothing behaves exactly as it did before.

## Other decisions

The request body parameter is named `body` rather than `json`, as the old client had it, so that it does not shadow the standard `json` module and reads plainly. It is passed to `requests` as `json=`.

`delete` accepts a `body`, which the old client did not. UBI's order routes merge the query string and the JSON body (`OrdersBlueprint._body`), so cancelling an order works with either.

`patch` was added at the user's request. UBI has no PATCH route yet, so a PATCH today gets HTTP 405 from Flask, which the client raises as `ServerError`.

`_send` is the only place that calls `requests`. It turns `requests.RequestException`, such as a refused connection or a timeout, into `UnreachableError`, chained with `from` so the original error is kept. The old client let those exceptions escape unchanged, even though its `UBIServerError` docstring claimed to cover them.

Until 2026-09-26 each request used `requests.request` directly rather than a `requests.Session`, on the grounds that a session must be closed. The client now keeps one session, because instruments_explorer sends thousands of requests through it; see below.

The old client repeated the parse-and-raise code in `connect`, `disconnect` and `status`. Now `disconnect` and `status` go through `_request` like every other route, and only `connect` builds its request by hand, because it sends the key and secret instead of a token.

## Verified on 2026-09-14

A live check against UBI on `http://127.0.0.1:8080` passed every case: connecting returned a 36-character token and an expiry one day later; `status()`, `/api/brokers/details` and `/api/instruments/segments` returned data; an invalid `instrument_id` raised `BadRequestError`; a PATCH raised `ServerError` with status 405; a stale token reconnected and succeeded with a new token; a wrong secret raised `AuthenticationError`; and a closed port raised `UnreachableError`.

## `placement_mode` and the per-request timeout, added on 2026-09-26

`placement_mode` records whether UBI was last seen placing orders through its order engine (`engine`) or directly (`direct`), and is None until an order has shown which. UBI has no route that reports its mode: `placement_mode` is only an attribute on its `OrdersBlueprint` and is never served. Engine mode does leave a mark on every answer to `POST /api/orders/place`, though, including dry runs and refusals, because `IntentHandoff.engine_answer` adds an `intent_id` to each one, and direct mode never adds it. `TradeableInstrument.place_order` reads that mark and stores the result here, so the probe it makes costs one dry run per client rather than one per order. It is a public attribute on the client rather than on the instrument because every instrument shares one client, and the mode belongs to the server the client talks to.

`post` takes an optional `timeout_seconds` that overrides the client's own 30 seconds for one request, passed down through `_request` and `_send`. It exists for `POST /api/orders/flatten`, which cancels every open order, waits up to five seconds for the cancels to be confirmed and then closes each position one after another, so an account with several positions can take well over 30 seconds to answer. Only `post` takes it, because no other route is that slow.

## The message falls back to `status_message`, since 2026-09-26

`_raise_for_failure` takes the exception's message from the body's `error` field. UBI's order engine does not use that field for its 504, "the engine did not answer in time": it answers with an order-shaped body whose explanation is in `status_message`, so the first dry runs against the engine on 2026-09-26 raised `OrderOutcomeUnknownError` with only "UBI returned HTTP 504". The method now falls back to `status_message` when there is no `error`, and to the generic text only when there is neither.

## Token sources, the session and the lock, since 2026-09-26

instruments_explorer, a long-running web application beside UBI, moved all of its UBI access onto this library on 2026-09-26. Three things it needed changed the client.

**Where the token comes from is now a separate object.** `token_source` is a `tradingmachine.ubi_client.token_sources.TokenSource`, asked for a token before each request (`current_token`), asked again once after a 401 (`token_after_refusal`), asked to connect by `connect()`, and told to forget its token by `disconnect()`. Leaving `token_source` out builds a `MongoCredentialTokenSource`, which is the code that used to be `_load_credentials` plus the old connect-on-first-use and reconnect-on-401 behaviour, so a client built the old way behaves exactly as before; `tests/test_client.py` pins that down. instruments_explorer instead passes `tradingmachine.ubi_stores.stored_login_token_source.StoredLoginTokenSource`, which uses the token UBI has already stored and connects only when none is usable, because that project's rule is never to connect while a stored token is usable. The actual exchange of key and secret for a token is the public `exchange_credentials`, so every source connects the same way and `token_expires_at` is always set by it.

A configuration is now built only when it is needed: when `base_url` is missing, or when no token source is given. A caller that passes both never causes the `.env` search, which matters because `Configuration` loads the `.env` it finds into `os.environ` for the whole process, and a host application must not pick up tradingmachine's variables by accident.

**One `requests.Session` with a pool of `connection_pool_size` connections** (10 by default) replaces `requests.request`. Reusing connections saves a TCP handshake per call; instruments_explorer's screener alone reads 750 stocks in one run. `close()` closes the pool, and the client works as a context manager, but a client that is never closed is harmless: the pool is released with the object. The session is only used for the thread-safe parts of `requests`: no cookies are set and nothing is mounted after construction.

**A lock around every call into the token source.** instruments_explorer calls the client from several threads at once. Without a lock, eight requests refused together would each connect, and each connect would replace the token the others had just received. `_token_lock` is a `threading.RLock` held while asking the source, never while a request is in flight, so requests still run in parallel. `CredentialTokenSource.token_after_refusal` returns the current token when it is no longer the refused one, which is how the seven threads that wait behind the first reuse its new token; `tests/test_token_sources.py` checks that eight concurrent refusals issue exactly one new token. The lock is re-entrant so that a source may call back into the client, as `connect` does through `exchange_credentials`.

The retry no longer recurses with an `is_retry` flag: `_request` sends, and on a 401 asks for a replacement token and sends exactly once more, raising whatever the second answer is. The observable behaviour is the same.

**Two new ways to send a request.** The `greeting` property sends `GET /api/`, the one route UBI serves without a token, and never asks the token source; instruments_explorer's status page uses it to tell "UBI is down" apart from "UBI has no token". `stream_get` sends an authenticated GET with `stream=True` and returns the open `requests.Response` once its status is known to be successful, retrying a 401 first, so a caller can read UBI's 127 MB instrument master as it arrives; `tradingmachine.ubi_client.instrument_master_stream.InstrumentMasterStream` is its only user.

A connect answer that carries no `access-token` now raises `ServerError` rather than a `KeyError`.
