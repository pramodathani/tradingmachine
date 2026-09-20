# src/tradingmachine/ubi_client/exceptions.py

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
