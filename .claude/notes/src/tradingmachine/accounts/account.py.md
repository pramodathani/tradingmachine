# src/tradingmachine/accounts/account.py

`Account.flatten` sends UBI's kill switch, `POST /api/orders/flatten`, which the Synthetic Order Atlas lists as row F2 and which UBI built as a route rather than an order type. The behaviour is described in `../unified_broker_interface/docs/rest-api/flatten.md`: it cancels every open order at every broker, re-reads the books until they confirm or it times out, and only then closes every position with limit orders.

## The shared client

`Account()` takes the client from `Instrument.shared_unified_broker_interface()`, which was made public for this. UBI holds one access token and every `connect` replaces it, so an `Account` with a client of its own would log every instrument out on its first request. A caller may still pass a client, as the instruments allow.

## `confirm` is typed by the caller

UBI refuses the request unless the body carries `confirm` set to exactly `FLATTEN`. The method could fill that in itself, but then one stray `flatten()` call would unwind the account, which is exactly what UBI's confirm word exists to prevent. So `confirm` is a required argument with no default, and the caller has to type the word. It is passed through unchecked, and UBI answers HTTP 400 for anything else.

## `dry_run` is sent as a real boolean

UBI reads `dry_run` with a plain Python `bool()` (`blueprints/orders.py`, in `flatten_everything`), so the string `"false"` would count as a dry run and `0` as a real one. The method sends `bool(dry_run)`, so the JSON always carries `true` or `false`. The quirk is recorded in this project's former Known issues page, which the documentation rebuild of 2026-09-26 removed and which `git show b5761c0:docs/contributing/known-issues.md` still prints.

## The timeout

Flatten waits up to five seconds for the cancellations and then closes each position one after another, and in engine mode each close waits for the engine's answer too. An account with several positions can take well over the client's default 30 seconds, so the method passes its own `timeout_seconds`, 120 by default, through the per-request override `post` gained for this. A timeout raises `UnreachableError`, but the flatten may have partly happened, so the docstring says to read the orders and positions before calling again rather than to retry.

## HTTP 207 is not an error

UBI answers 200 when everything asked for was done and 207 when any part was not, including a close the broker refused. Both are successes to the client, so nothing is raised and the answer's `flat` field is what says whether the account is flat. The method returns the answer as it came rather than raising on `flat: false`, because the caller needs the `closed` entries to see what is left.

## What it does not do

UBI's kill switch reads only the brokers' order books and positions. An armed synthetic order in UBI's engine, such as a hidden stop, a grid or an exposure hedge, is not a broker order, so a flatten does not disarm it, and it can trade again afterwards. UBI also has no REST route to list or cancel such a parent. And in engine mode the closes go wherever the broker selector sends them rather than to the broker holding the position. All three are UBI's to fix and are recorded in this project's former Known issues page, which the documentation rebuild of 2026-09-26 removed and which `git show b5761c0:docs/contributing/known-issues.md` still prints; the docstring warns about each.
