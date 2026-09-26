# src/tradingmachine/unified_broker_interface/exceptions.py

This module defines the errors the UBI client raises. It was adapted from `src/tradingmachine/ubi_client/exceptions.py` in the old tradingmachine project, kept at `/run/media/pramod/6959D90B1DAD7E59/backup_20260910/pramod/Downloads/tradingmachine-master/`.

## Why the classes are keyed on the HTTP status code

UBI reports failures in plain REST style: a non-2xx status code with a JSON body shaped `{"error": message, ...}`. There is no error-type field in the body to switch on, so the status code alone chooses the class. `EXCEPTION_FOR_STATUS_CODE` holds that mapping, and `UnifiedBrokerInterface._raise_for_failure` in `client.py` uses it, falling back to `ServerError` for any status without its own class.

## Status codes, checked against UBI's source on 2026-09-14

The old project handled 400, 401, 404, 429 and 502. The current UBI also returns 409, 422, 503 and 504, so those were given classes too.

| Status | Class | Where UBI returns it |
|---|---|---|
| 400 | `BadRequestError` | `RequestError` raised by parameter parsing in `instrument_identity.py`, `instrument_history.py` and the order write service |
| 401 | `AuthenticationError` | The `authenticated` decorator in `blueprints/base.py`, and a wrong key or secret in `blueprints/session.py` |
| 404 | `NotFoundError` | Missing user profile, empty collections, unknown instruments, orders not in the book |
| 409 | `ConflictError` | Modifying or cancelling an order that is no longer pending or open |
| 422 | `OrderRejectedError` | Order outcome `rejected` (`OUTCOME_STATUSES` in `write_service.py`) |
| 429 | `RateLimitError` | The chosen broker is at its order rate limit |
| 502 | `BrokerError` | `unified_documents.py`, when no broker's data could be read, and an unreadable order book |
| 503 | `ServiceUnavailableError` | A stale or missing Redis document, no instruments mapped yet, an unreachable instrument cache, or no broker able to take an order |
| 504 | `OrderOutcomeUnknownError` | Order outcome `unknown` |
| 500 and others | `ServerError` | The UBI settings document is missing; 405 when a route does not accept the method |
| none | `UnreachableError` | Raised by the client itself when `requests` fails before a response arrives |

For 422 and 504, UBI returns the order document rather than an `{"error": ...}` body, so the message falls back to `UBI returned HTTP <status>` and the order document is in `detail`.

## Differences from the old module

The old project prefixed every class with `UBI`, as in `UBINotFoundError`. The prefix was dropped because the module path already names the service, and the Google style guide advises against repetition such as `foo.FooError`. The base class is spelled out in full as `UnifiedBrokerInterfaceError`.

The old `UBIRateLimitError.retry_after_seconds` property was dropped. The current UBI builds its 429 body from `RequestError`, which only carries a message, so `retry_after_seconds` is never in the body.

The old free-standing function `raise_for_response` became the client method `_raise_for_failure`, because the user's rules put behaviour on classes.

`detail` is set to an empty dict when there was no body, as in the old module, so callers can call `detail.get(...)` without first checking for `None`.

## The order engine's status codes, added on 2026-09-26

UBI gained an order engine on 2026-09-23, and when it runs in engine mode (`UNIFIED_BROKER_INTERFACE_API_ORDER_PLACEMENT=engine`) `POST /api/orders/place` can answer with codes and meanings that direct mode never produced. The source is `../unified_broker_interface/docs/rest-api/order-engine.md`, in the table of engine-only answers.

| Status | Engine meaning | Class |
|---|---|---|
| 202 | A synthetic order is armed or scheduled and nothing has reached a broker yet | none, because a 2xx is a success and the client returns the body |
| 403 | The daily loss lockout is on | `LossLockoutError`, new |
| 409 | The intent went stale, or a quantity reference asked to reduce or close a position that is not held | `ConflictError`, with its docstring widened |
| 429 | The broker's daily order cap has no room for this kind of order | `RateLimitError`, with its docstring widened |
| 503 | A price reference could not be resolved (no quote, a book too shallow, no agreed tick size), or the rate budget is full | `ServiceUnavailableError`, with its docstring widened |
| 504 | The engine did not answer in time, so the order may still be placed | `OrderOutcomeUnknownError`, unchanged |

`LossLockoutError` is named for what the 403 means rather than called `ForbiddenError`, because the loss lockout is the only thing UBI answers 403 for, and a caller who catches it wants to know that the day is over, not that a permission is missing. `POST /api/orders/flatten` also answers 207 when part of it failed; that is a 2xx as well, so it is read from the body's `flat` field rather than raised.

`DirectPlacementError` is the one class not produced by a status code. The client raises it itself, with `status_code=None`, when UBI turns out to be in direct mode and the order carries a `price_reference`, a `quantity_reference` or a `synthetic` object. In direct mode UBI validates those objects' shapes and then ignores them, so a bracket goes out as an unprotected entry and a limit order carrying only a price reference goes out at price 0, and UBI refuses none of it. The check that raises it lives in `TradeableInstrument.place_order`; see the note on `src/tradingmachine/assets/instruments.py`.
