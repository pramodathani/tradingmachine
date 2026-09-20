# assets/instruments.py

This module holds `Instrument`, `TradeableInstrument` and `NonTradeableInstrument`. They were ported on 2026-09-14 from `assets/instruments.py` in the old tradingmachine project at `/run/media/pramod/6959D90B1DAD7E59/backup_20260910/pramod/Downloads/tradingmachine-master/`. The other classes in that file (`HoldableInstrument`, `Futures`, `Option`, `ListedSecurity`, `UncategorisedInstrument`) were out of scope and are not ported yet. `TradeableInstrument` gained its order, trade and position members on 2026-09-20, which is described under "The order surface" below and is a fresh build rather than a port.

## What changed in UBI since the old code

The old code was already written against UBI, but an earlier version of it. Porting meant following these changes:

| Topic | Old code assumed | UBI on 2026-09-14 |
|---|---|---|
| Exchange names | `NSE`, upper case | `nse`, lower case |
| Instrument key | A colon string built locally, such as `NSE:equities:INFY` | `instrument_id`, a UUID5 UBI computes from the identity, returned by `/api/instruments/details` |
| Segment | Bare, such as `equities` | Accepted bare or prefixed, and always returned prefixed, such as `nse_equities` |
| Quote fields | `ltp`, `bids`, `asks`, `upper_circuit`, `lower_circuit`, `total_traded_value`, `last_traded_quantity` | `last_price`, `depth.buy`, `depth.sell`, `average_price`, `volume`, `oi`, `last_quantity`; no circuit limits and no traded value |
| Candles | A list of objects with a `datetime` key | A `columns` list and rows of `time, open, high, low, close, volume, oi`, plus `price_factor` when adjusted |
| Lot and tick size | Read from the first `carried_by` entry | Top-level `lot_size` (int) and `tick_size` (str in rupees) on `/details` |

## Construction

The constructor sends one `GET /api/instruments/details`. It sends `instrument_id` alone when given; otherwise it sends every lookup argument that is not None. UBI decides which identity fields a segment's shape needs and answers HTTP 400 with a clear message when some are missing, so the class keeps no local segment table. The old project fetched `/api/instruments/segments` into `assets/segments.py` for that purpose, and it is not needed now.

A 404 becomes `InstrumentError`, chained with `from`, because "no such instrument" is a domain problem. A 400 is left as `BadRequestError`, because it is a malformed call and UBI's message already says what is wrong.

After construction, every request sends only `instrument_id`, which names the instrument exactly and avoids re-parsing identity fields on every call.

Identity values are stored as UBI returns them, which is the canonical form: the exchange in lower case, the segment prefixed, and symbols in upper case. Dates become `datetime.date`. They are plain public attributes rather than properties, because Google style guide rule 2.13 does not allow a property that only reads an attribute.

`__eq__` and `__hash__` use `instrument_id`, so an instrument built by id equals the same instrument built from its fields. The live check on 2026-09-14 confirmed this for INFY and for a NIFTY option.

## repr

`__repr__` originally formatted every identity value with `str(value)!r`. That was aimed at dates, so an expiry would read `'2026-09-29'` rather than `datetime.date(2026, 9, 29)`, but it quoted everything else too, and a strike price came out as `strike_price='1250.0'` as though it were text. The fault surfaced on 2026-09-20 while verifying `assets/equities.py`, whose segment-check messages embed `{self!r}`.

It now converts only dates, with `value.isoformat()`, and passes every other value to `!r` unchanged, so a strike reads `strike_price=1250.0`. Dates keep the ISO form deliberately, because that is one of the two forms the constructor accepts, which a `datetime.date(...)` repr is not.

## Lot size and tick size

The old rule took `lot_size` and `tick_size` from the first entry in `carried_by`. When porting, UBI's brokers turned out to disagree on units:

- Tick size for NSE equities was in paise at Dhan, INDmoney, Kotak and Stoxkart, and in rupees elsewhere.
- Lot size for MCX GOLD was 100 at Groww and 1 at the other brokers.

Because `carried_by` is alphabetical, the first entry was Dhan, which gave INFY a tick size of 10 instead of 0.1.

The user fixed this inside UBI in a separate session on 2026-09-14. UBI's mapping now converts tick sizes to rupees in tradeable segments. `/details` also gained top-level `lot_size` and `tick_size`, which are the values meant for the instrument itself:

- `lot_size` is underlying units per lot, decided the same way the unified quote decides it: 1 for a security, Groww's figure on MCX, and the brokers' majority elsewhere.
- `tick_size` is the value most brokers agree on.
- Either is null on a tie, and UBI leaves index and uncategorised tick sizes unconverted.

`Instrument` reads these two fields, converting `tick_size` to `decimal.Decimal` so a price step like 0.05 stays exact. It reads them with `dict.get`, so a UBI process started before the change gives None rather than failing. `carried_by` stays available raw for code that needs one broker's own figures, such as an order sent to a particular broker. On MCX those figures mean different things at different brokers.

## Shared client

UBI holds one access token for the whole application, and every connect replaces it (see `.claude/notes/ubi_client/client.py.md`). If each instrument created its own `UnifiedBrokerInterface`, the instruments would keep logging each other out, and each would pay a reconnect on its next call. Instruments therefore share one client, created on first use by `_get_shared_unified_broker_interface`. It is stored on `Instrument` by name rather than through `cls`; assigning through `cls` would give each subclass its own attribute and its own client. A caller can still pass its own client.

## No caching and no batching

Every call goes straight to UBI. The old project cached candles in Redis for 5 minutes and quotes for 5 seconds, kept warm by a poller, and had a stub for a websocket source. The user decided on 2026-09-14 that none of this carries over: UBI runs on the same machine and caches in its own Redis, and its `/prices` endpoint serves any date range in one request.

So an indicator method fetches its own candles, and `bid_offer_spread` fetches one quote per call. Methods that need two values from the same moment, `bid_offer_spread` and `mid_price`, read both from a single quote rather than calling `best_bid` and `best_offer`, which would fetch twice and could mix two different moments.

## Live values are methods

The old code exposed `ltp`, `best_bid`, `vwap` and the other quote values as properties. Here they are methods, because each is a network call, and Google style guide rule 2.13 allows properties only for cheap computations.

`quote`, `last_price` and `ohlc` sit on `Instrument` rather than `TradeableInstrument`, because UBI quotes indices too, and an index's last price is one of the most used values. The order-book methods sit on `TradeableInstrument`, because an index has no order book.

The old `bids` and `asks` filtered out zero-price levels. UBI now drops empty levels itself, as `docs/architecture/contracts.md` in UBI states, so the filter is gone.

| Old | New | Notes |
|---|---|---|
| `quote` property | `quote()` on `Instrument` | Full unified quote dict |
| `ltp` | `last_price()` on `Instrument` | Uses `/api/instruments/ltp` |
| `ohlc` | `ohlc()` on `Instrument` | Uses `/api/instruments/ohlc`; `ohlc` has no close, but the dict has `previous_close` |
| `bids`, `asks` | `bids()`, `asks()` | From `depth.buy` and `depth.sell` |
| `best_bid`, `best_offer`, `bid_offer_spread`, `mid_price` | Same names, as methods | |
| `vwap` | `volume_weighted_average_price()` | UBI's `average_price` |
| `last_traded_quantity` | `last_quantity()` | Underlying units, not lots |
| `total_traded_volume` | `total_traded_volume()` | UBI's `volume` |
| `last_traded_at` | `last_trade_time()` | Epoch seconds turned into an India-time `datetime` |
| none | `open_interest()` | New; UBI's `oi` |
| `upper_circuit`, `lower_circuit`, `total_traded_value` | dropped | UBI no longer provides them |

## prices

`prices` renames UBI's `time` column to `datetime`, as the old frame had it, and converts it from UTC to India time. A daily candle therefore reads `2026-09-09 00:00:00+05:30` rather than `2026-09-08 18:30:00+00:00`. The frame keeps UBI's extra `oi` and `price_factor` columns. The `exchange`, `segment` and `interval` columns are inserted in front, as in the old code. The frame is sorted by time as a safeguard, because the adjusted-bars SQL function's ordering is not documented.

`adjusted` is sent as the text `true` or `false`, which UBI's `parse_bool` reads, rather than relying on how `requests` would print a Python bool.

## Tradeable or not

A segment ending in `_indices` is an index and cannot be traded; every other segment can. This is the old rule. It works on UBI's prefixed segment names too, such as `nse_equity_indices`. The check runs after the details are fetched, so a wrong class costs one request before it raises.

## The order surface

`TradeableInstrument` gained seven members on 2026-09-20: `place_order`, `modify_order`, `cancel_order`, `orders`, `trades`, and the `net_positions` and `day_positions` properties. They sit on `TradeableInstrument` rather than on `Instrument` because an index has no orders, no trades and no position. Holdings and funds were left out of this change, and holdings stay on `Equity` in `assets/equities.py`, where they belong.

This is a fresh build against UBI's current contract, not a port. The old project's order methods were written against a much earlier UBI, and every name in them has since changed:

| Topic | Old code | UBI today |
|---|---|---|
| Order handle | An opaque encrypted `reference` | The broker's own `order_id`, plus an optional `broker` when two brokers share an id |
| Side | `side`, values `buy` and `sell` | `transaction_type`, values `BUY` and `SELL` |
| Product | `delivery`, `intraday`, `carry` | `CNC`, `MIS`, `NRML` |
| Order type | `market`, `limit`, `stop_loss`, `stop_loss_market` | `MARKET`, `LIMIT`, `SL`, `SL-M` |
| Filtering to one instrument | Matched `exchange` and `symbol` | Every row carries UBI's `instrument_id` |
| Positions | Never implemented | `/api/portfolio/positions`, with `net` and `day` buckets |

The old project also had sixteen convenience wrappers over `place_order`, such as `buy_at_market_price` and `buy_at_midprice`. The user decided on 2026-09-20 not to bring them across; a caller writes the `place_order` call itself.

### Vocabulary is plain strings

`transaction_type`, `order_type`, `product` and `validity` are passed as plain strings, with no constants and no enum classes, which the user chose on 2026-09-20 over module constants and over a separate `assets/orders.py`. UBI parses these fields case-insensitively and upper-cases them, so `"buy"` and `"limit"` reach the broker correctly, and UBI's own 400 is the single source of truth for what is allowed. This matches how `exchange`, `segment`, `option_type` and the candle `interval` are already handled.

### Nothing is validated before sending

The price and quantity go to UBI exactly as the caller gave them. There is no tick rounding, no lot-multiple check and no expiry check, which the user chose on 2026-09-20 over both a local guard and silent rounding. UBI and the broker already hold those rules, `lot_size` and `tick_size` are null whenever UBI's brokers disagree, and a broker's rejection is the correct and informative failure. This is the same reasoning as "No caching and no batching" above: do not build a second copy of what UBI already does.

The one thing worth knowing is how UBI couples the price fields to the order type, because the class does not enforce it and a caller will meet it as a `BadRequestError`. A `LIMIT` or `SL` order needs a price, an `SL` or `SL-M` order needs a trigger price, and a `MARKET` or `SL-M` order must carry no price at all. This is why every optional field in `place_order` defaults to `None` and is added to the body only when it is not `None`. A default of `0` for `price`, which the old code used, would make every market order fail.

### Why filtering happens here

None of UBI's read routes filter. `/api/orders/details`, `/api/orders/trades` and `/api/portfolio/positions` take no parameters at all and return the whole account across all ten brokers, and there is no route for a single order. Each is a single Redis read of a document UBI rewrites twice a second, so fetching the whole book per instrument is the intended usage.

Every order, trade and position row carries `instrument_id`, so `_frame_for_this_instrument` filters on one predicate. It is deliberately simpler than `Equity.holdings`, which needs a symbol fallback because UBI merges holdings across exchanges under whichever broker's row arrived first. Orders and trades are not merged at all, and positions are merged by instrument and product, so the id is enough in both cases.

Two consequences are written into the docstrings. A row whose `instrument_id` is null, which happens when UBI could not resolve a broker's token, is invisible to the filter, and there is no clean fallback, because a row's `exchange` is the broker's own code such as `NSE_EQ` and its `tradingsymbol` is the broker's own spelling such as `NIFTY25SEP24000CE`. And because orders and trades are not merged, the same instrument traded at two brokers gives one row from each.

### Return shapes

`orders`, `trades`, `net_positions` and `day_positions` return a `pandas.DataFrame`, or `None` when no row matches, which the user chose on 2026-09-20 over lists of dicts. This follows `prices`, which also returns `None` rather than an empty frame.

`place_order` returns UBI's whole response dict rather than the bare order id the old code returned. The caller needs `broker` from it, because two brokers can hold the same `order_id` and a later modify then has to say which one, and it needs `outcome`, because `order_id` is null unless the order was accepted.

The net bucket's member is called `net_positions` rather than plain `positions`, which the user asked for on 2026-09-20 so that the pair names the two buckets UBI actually serves. A bare `positions` beside a `day_positions` reads as though it were the whole of them rather than one of two, and the difference between them matters: net counts everything open now, however long it has been open, while day counts only what today opened.

`net_positions` and `day_positions` are properties rather than methods, which the user chose on 2026-09-20. This extends the exception recorded under "Holdings, and why it is a property" in `.claude/notes/assets/equities.py.md`: a member reporting what the account currently owns or owes is a property, while a member reporting a market value, such as `quote` or `last_price`, stays a method. Each read still sends a request, so code that needs the frame twice should bind it to a local variable.

### Order id, not instrument

`modify_order` and `cancel_order` take an `order_id` and send it straight through. They do not check that the order belongs to the instrument they were called on, which the user chose on 2026-09-20 over fetching the order book first to verify. UBI finds the order by id across the brokers' books, so the check would cost an extra request on every call and would only catch a caller using the wrong object. The wart to know about is that cancelling from the wrong instrument still works.

`dry_run` is exposed on all three writing methods. UBI builds the broker's request and returns it without sending, which is the only way to see the exact form UBI will post.

### No new exception classes

`assets/exceptions.py` did not change. Because nothing is validated locally, there is no domain error to raise, and `ubi_client/exceptions.py` already maps every status these routes return: 409 to `ConflictError`, 422 to `OrderRejectedError`, 429 to `RateLimitError` and 504 to `OrderOutcomeUnknownError`. Those four classes were added in September for exactly this, before any order method existed.

Two of them deserve care from callers. A 504 `OrderOutcomeUnknownError` means the order was sent and its fate is unknown, so the order book must be read before sending it again. A 503 from a read route does not mean a broker is down; it means UBI's own background aggregator stopped writing the document.

## Verified on 2026-09-14

A live check against UBI on `127.0.0.1:8080`, from a scratchpad script, confirmed the following:

- INFY built as `TradeableInstrument` and again by `instrument_id`, and the two were equal.
- `prices(days=400)` returned 270 daily candles; a `from_date` and `to_date` range and `adjusted=False` also worked.
- `last_price`, `ohlc`, `quote` and `last_trade_time` returned values after hours, while the order-book methods returned None because depth was empty.
- NIFTY built as `NonTradeableInstrument` and returned a last price.
- A NIFTY option built by id and again from its identity fields, and the two were equal.
- Errors surfaced correctly: an unknown symbol raised `InstrumentError`, an index as tradeable raised `TradeableInstrumentError`, a stock as non-tradeable raised `NonTradeableInstrumentError`, and both `days` with `from_date` and a future without an expiry raised `BadRequestError`.

The top-level `lot_size` and `tick_size` were checked later that day, after the user restarted UBI's REST API service at 20:09 IST.

| Instrument | `lot_size` | `tick_size` | What the brokers' own figures showed |
|---|---|---|---|
| NSE INFY, NSE RELIANCE | 1 | 0.1 | All brokers agree, except Flattrade, which sends no tick size |
| MCX GOLD, expiry 2026-10-05 | 100 | 1 | Groww's lot of 100 is chosen over the other brokers' 1, as UBI's rule says |
| NSE NIFTY index | 1 | 0.05 | Brokers send eight different pairs, including 0, -1 and a lot of 2000; UBI's majority still gave 0.05 |
| NSE NIFTY futures, three expiries | 65 | 0.1 | Not compared per broker |

Index tick sizes are left unconverted by UBI (its `docs/contributing/known-issues.md`), so an index's `tick_size` rests on a majority of mixed units and is less trustworthy than a tradeable segment's.

## The order surface, verified on 2026-09-20

A live check against UBI on `127.0.0.1:8080`, from a scratchpad script, covered everything that can be checked without placing an order.

The account held exactly one order that day, a cancelled `indmoney` limit buy of one KWIL share at 40.4, and no trades and no positions. That was enough to test the filter in both directions. `TradeableInstrument(instrument_id="005799f8-f4b5-507b-a1bd-7a6aecd260fd")` resolved to KWIL and its `orders()` returned a one-row frame of 26 columns holding that order, while `orders(open_only=True)` correctly returned None, because `CANCELLED` is a terminal status. An `Equity` for RELIANCE, which had no orders, returned None from `orders`, `trades`, `net_positions` and `day_positions`.

A dry run of `place_order` on KWIL, asking for a limit buy of one share at 30.0 with `transaction_type="buy"`, `order_type="limit"` and `product="cnc"` all in lower case, came back with UBI having chosen `shoonya` and built this form for it:

```
prctyp=LMT  trantype=B  prd=C  ret=DAY  qty=1  prc=30.0  trgprc=0  dscqty=0  amo=NO  tsym=KWIL-EQ
```

That confirms the lower-case strings survive UBI's parsing, that the body is assembled correctly, and that the optional fields left as None are genuinely absent rather than sent as zeros. The coupling rules fired as expected: a market order carrying a price raised `BadRequestError: a MARKET order takes no price`, and a limit order with no price raised `BadRequestError: a LIMIT order needs a price`.

What this check does not cover is `modify_order` and `cancel_order` against a real order, because both look the order up in the broker's live book and answer 404 for an id that does not exist. That run needs a genuine order and has to be started by the user, for the reason recorded in `.claude/notes/ubi_client/client.py.md` and in the session memory: Claude Code's permission classifier blocks order placement.
