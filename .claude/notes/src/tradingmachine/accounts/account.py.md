# src/tradingmachine/accounts/account.py

`Account.flatten` sends UBI's kill switch, `POST /api/orders/flatten`, which the Synthetic Order Atlas lists as row F2 and which UBI built as a route rather than an order type. The behaviour is described in `../unified_broker_interface/docs/rest-api/flatten.md`: it cancels every open order at every broker, re-reads the books until they confirm or it times out, and only then closes every position with limit orders.

## The shared client

`Account()` takes the client from `Instrument.shared_unified_broker_interface()`, which was made public for this. Sharing it keeps one cached access token and one place that reconnects after HTTP 401, as the instruments do. A caller may still pass a client, as the instruments allow.

## `confirm` is typed by the caller

UBI refuses the request unless the body carries `confirm` set to exactly `FLATTEN`. The method could fill that in itself, but then one stray `flatten()` call would unwind the account, which is exactly what UBI's confirm word exists to prevent. So `confirm` is a required argument with no default, and the caller has to type the word. It is passed through unchecked, and UBI answers HTTP 400 for anything else.

## `dry_run` is sent as a real boolean

UBI reads `dry_run` with a plain Python `bool()` (`blueprints/orders.py`, in `flatten_everything`), so the string `"false"` would count as a dry run and `0` as a real one. The method sends `bool(dry_run)`, so the JSON always carries `true` or `false`. The quirk is recorded in this project's former Known issues page, which the documentation rebuild of 2026-09-26 removed and which `git show b5761c0:docs/contributing/known-issues.md` still prints.

## The timeout

Flatten waits up to five seconds for the cancellations, sends every close to the order engine at once, waits for the engine's answers, and then waits up to five more seconds for the brokers' positions to show zero. That can take well over the client's default 30 seconds, so the method passes its own `timeout_seconds`, 120 by default, through the per-request override `post` gained for this. A timeout raises `UnreachableError`, but the flatten may have partly happened, so the docstring says to read the orders and positions before calling again rather than to retry.

## HTTP 207 is not an error

UBI answers 200 when everything asked for was done and 207 when any part was not, including a close the broker refused. Both are successes to the client, so nothing is raised and the answer's `flat` field is what says whether the account is flat. The method returns the answer as it came rather than raising on `flat: false`, because the caller needs the `closed` entries to see what is left.

## What it did not do, and what UBI fixed on 2026-09-26 and 2026-09-27

Three gaps were recorded here when the method was written, and UBI has closed all three:

| Gap | Fixed by UBI |
|---|---|
| An armed synthetic order, such as a hidden stop or a grid, survived a flatten and could trade again afterwards | Flatten now sends a `halt` command first, which ends every open parent as `cancelled` and reports how many under `halted` |
| There was no REST route to list or cancel a parent | `GET /api/orders/parents` and `DELETE /api/orders/parents`, which `Account.parents` and `TradeableInstrument.cancel_parent` use |
| Closes went wherever the broker selector sent them rather than to the broker holding the position | Each close is sent to the broker holding its position, and `flat` is true only once the brokers' positions show zero |

The docstring was rewritten to describe the new behaviour, and the answer's two new fields, `halted` and `positions_still_open_after_waiting`, were added to it. A close is a market order, which the old docstring had wrongly called a limit order.

## `parents` and `intent`, added on 2026-09-27

`parents` lists every open parent in the account, and `intent` reads `GET /api/orders/intents/<intent_id>`, which returns the engine's answer to an order whose placement stopped waiting, for five minutes by default. Both live here rather than on an instrument because neither is tied to one instrument: an intent that timed out may be for any instrument, and the whole list of parents is what a person looks at after a flatten or a restart.
