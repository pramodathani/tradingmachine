# Known issues

Things that are wrong or missing, as opposed to things that are merely surprising. The surprising
ones are on [Pitfalls](pitfalls.md).

## In UBI, not here

These are recorded because the first person to hit them will need somewhere to start. Nothing in
this project works around any of them; the fix belongs in UBI.

### Bond derivatives are routed to the wrong venue

UBI classifies `fixed_income_futures`, `fixed_income_options` and `fixed_income_index_futures`
under its `securities` asset class, so their market tuple resolves to the equity derivative venue
although the instruments are sourced from the currency-derivative files. The same misclassification
means the quantity is sent in plain units although rate futures are lot-quoted, and that the session
window closes at 16:00 although these contracts trade until 17:00.

This is inference from reading UBI's source on 2026-09-20, not a verified observation, because
verifying it would mean sending a real order.

### Four segments are permanently or indefinitely empty

| Segment | Class | Outlook |
| --- | --- | --- |
| `currency_indices` | `CurrencyIndex` | India has no traded currency index, so unlikely ever to populate |
| `currency_index_futures` | `CurrencyIndexFutures` | The same |
| `currency_index_options` | `CurrencyIndexOption` | The same |
| `fixed_income_index_options` | `FixedIncomeIndexOption` | No mapping rule exists in UBI at all today |

The classes exist so that each family has the same shape, and they degrade cleanly.

### No candles for whole families

UBI stores no candles for any fixed income or currency segment, none for investment trusts, and
none for mutual funds. The roughly 190 analysis methods are present on those instruments and have
nothing to work on.

UBI's own source comment saying "no derivative bars are stored yet" is stale, by the way: commodity
derivatives do have candles, which was measured rather than inferred.

### A bond held only at one broker is not reported

UBI resolves a Groww holding by the ticker the broker sends rather than by a token, and then looks
that ticker up among fixed income symbols that are ISINs, which never matches. A bond held only
there is missing from the holdings document entirely.

### One broker's currency derivatives are dropped from the tick streams

Its fixed divisor is a hundred times wrong for four-decimal pairs, so UBI leaves them out rather
than publishing wrong prices.

### No route says whether the order engine is running

A `price_reference`, a `quantity_reference` or a `synthetic` object only works when UBI runs its
order engine, and in direct mode UBI checks their shape and then silently ignores them. UBI has no
route that reports which mode it is in, so `place_order` sends a dry run first and looks for the
`intent_id` the engine adds to every answer. One field on an authenticated route would make that a
single read. See [Orders](../guides/orders.md).

### An engine order cannot be listed or cancelled

A synthetic order that is waiting, such as a hidden stop or a scheduled order, has a `parent_id` but
no broker order yet, and UBI has no REST route to list parents or cancel one. The only way to stop
one today is inside UBI itself.

### `flatten` leaves the engine's orders armed

`POST /api/orders/flatten` reads only the brokers' order books and positions, so an armed hidden
stop, grid, exposure hedge or any other waiting synthetic order survives it and can trade again
afterwards. In engine mode its closing orders also go wherever UBI's broker selector sends them,
rather than to the broker holding each position, and they are not marked as closing a position, so
they cannot use the exit share of a broker's daily order cap.

### `flatten` reads `dry_run` loosely

UBI reads the field with Python's `bool()`, so the string `"false"` counts as a dry run and `0` as a
real one. `Account.flatten` always sends a real JSON boolean, so this only matters to other callers.

### Most of the Atlas's extra order types are not built

UBI's order engine was designed from the Synthetic Order Atlas, and it builds every type in the
Atlas's first six groups that can be built at all. The Atlas's seventh group, G, is seventeen more
types from a second sweep of broker catalogues. It is outside that count, and as of 2026-09-26 most of
it is missing:

| Status | Group G types |
| --- | --- |
| Covered under another name | Snap order (a price reference on a plain order), midprice order (`peg` at the midpoint), scale order with profit-taker (`grid`) |
| Partly covered | Adjustable stop (only `scale_out`'s move to breakeven), stops triggered by something other than the last price (`hidden_stop` watches the bid and offer, `indicator_triggered` watches a quote field), reduce-only (only the `reduce_position` quantity reference), close-on-trigger (only `square_off` and `flatten` cancel first), attached hedge (`exposure_hedge`, with no delta) |
| Missing | Opening-auction order, closing-price order, limit that turns into market at a time, pegged to underlying, volatility order, trailing take-profit with an activation price, stop-and-reverse, two-sided quote, account-state conditional |

Order types are built in UBI rather than here, so these belong in the sibling project. The status
column comes from reading UBI's engine source for each type, not from placing orders.

## In this project

### There is no test suite

`pytest` is not in `requirements.txt` and is not installed. Nothing here has automated tests. What
verification exists is recorded in the sidecar notes under `.claude/notes/`, as live checks against
a running UBI on a stated date, and each note says plainly whether any order was sent.

This is not only inertia: as [Pitfalls](pitfalls.md#testing-means-placing-real-orders) explains,
testing the order paths against UBI means placing real orders.

### Redis and TimescaleDB are unused

Both containers are brought up by `docker-compose.yml` and neither is read by any Python module.
They are in place for a storage layer that has not been written.

### Most of the dependency list is unused

`requirements.txt` pins `streamlit`, `Flask`, `textual`, `uvicorn`, `gunicorn`, `yfinance`,
`selenium`, `SQLAlchemy`, `peewee`, `opstrat` and the websocket libraries, none of which any module
imports today. They describe the intended scope rather than the current one.

### The `uncategorised` segment is not ported

It is UBI's catch-all for rows whose identity could not be resolved, and UBI does not accept orders
for it. With that one exception, every asset class the old project had is now ported.
