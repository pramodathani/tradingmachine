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
