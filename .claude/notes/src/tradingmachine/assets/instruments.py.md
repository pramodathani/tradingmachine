# src/tradingmachine/assets/instruments.py

This module holds `Instrument`, `TradeableInstrument` and `NonTradeableInstrument`. They were ported on 2026-09-14 from `src/tradingmachine/assets/instruments.py` in the old tradingmachine project at `/run/media/pramod/6959D90B1DAD7E59/backup_20260910/pramod/Downloads/tradingmachine-master/`. The other classes in that file (`HoldableInstrument`, `Futures`, `Option`, `ListedSecurity`, `UncategorisedInstrument`) were out of scope and are not ported yet. `TradeableInstrument` gained its order, trade and position members on 2026-09-20, which is described under "The order surface" below and is a fresh build rather than a port.

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

The constructor sends one `GET /api/instruments/details`. It sends `instrument_id` alone when given; otherwise it sends every lookup argument that is not None. UBI decides which identity fields a segment's shape needs and answers HTTP 400 with a clear message when some are missing, so the class keeps no local segment table. The old project fetched `/api/instruments/segments` into its own `assets/segments.py` for that purpose, and it is not needed now.

A 404 becomes `InstrumentError`, chained with `from`, because "no such instrument" is a domain problem. A 400 is left as `BadRequestError`, because it is a malformed call and UBI's message already says what is wrong.

After construction, every request sends only `instrument_id`, which names the instrument exactly and avoids re-parsing identity fields on every call.

Identity values are stored as UBI returns them, which is the canonical form: the exchange in lower case, the segment prefixed, and symbols in upper case. Dates become `datetime.date`. They are plain public attributes rather than properties, because Google style guide rule 2.13 does not allow a property that only reads an attribute.

`__eq__` and `__hash__` use `instrument_id`, so an instrument built by id equals the same instrument built from its fields. The live check on 2026-09-14 confirmed this for INFY and for a NIFTY option.

## repr

`__repr__` originally formatted every identity value with `str(value)!r`. That was aimed at dates, so an expiry would read `'2026-09-29'` rather than `datetime.date(2026, 9, 29)`, but it quoted everything else too, and a strike price came out as `strike_price='1250.0'` as though it were text. The fault surfaced on 2026-09-20 while verifying `src/tradingmachine/assets/equities.py`, whose segment-check messages embed `{self!r}`.

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

UBI holds one access token for the whole application, and every connect replaces it (see `.claude/notes/src/tradingmachine/ubi_client/client.py.md`). If each instrument created its own `UnifiedBrokerInterface`, the instruments would keep logging each other out, and each would pay a reconnect on its next call. Instruments therefore share one client, created on first use by `shared_unified_broker_interface`. It is stored on `Instrument` by name rather than through `cls`; assigning through `cls` would give each subclass its own attribute and its own client. A caller can still pass its own client.

## No caching and no batching

Every call goes straight to UBI. The old project cached candles in Redis for 5 minutes and quotes for 5 seconds, kept warm by a poller, and had a stub for a websocket source. The user decided on 2026-09-14 that none of this carries over: UBI runs on the same machine and caches in its own Redis, and its `/prices` endpoint serves any date range in one request.

So an indicator method fetches its own candles, and `bid_offer_spread` fetches one quote per read. The members that need two values from the same moment, `bid_offer_spread` and `mid_price`, read both from a single quote rather than reading `best_bid` and `best_offer`, which would fetch twice and could mix two different moments.

## Live values are properties

Every member that only reports a value is a property. That covers `quote`, `last_price` and `ohlc` on `Instrument`, the eleven order-book values on `TradeableInstrument`, and the five members that read the order and trade books.

This reverses the decision recorded here on 2026-09-20 and was made by the user on 2026-09-22. The old reading leaned on Google style guide rule 2.13, which allows a property only for a cheap and unsurprising computation, and treated a network call as too expensive to hide behind attribute syntax. The user overruled it for the reason the rule exists in the first place, which is that the caller should read what the member means rather than how it is fetched. `share.last_price` is the share's last price, and the fact that the figure comes over HTTP from a service on the same machine is an implementation detail. The cost argument was also weaker than it looked, because UBI is local and answers from its own Redis, and because the members that report what the account owns, such as `net_positions` and `Equity.holdings`, were already properties and already sent a request on every read. Having half the live values as properties and half as methods was the real surprise.

What stayed a method is anything that takes an argument or does something. `prices` takes an interval and a date range, so it is a method. `place_order`, `modify_order`, `cancel_order`, `cancel_open_orders`, the twenty-eight priced wrappers and the four position-changing members all write to the market, so they are methods however few arguments they take.

The cost of the change is that a loop reading the same property twice now sends two requests without the parentheses to warn you. Code that needs a value more than once should bind it to a local variable, which is the same advice that already applied to `net_positions`.

The dated records of live checks further down this note were written before 2026-09-22 and keep the call syntax of the day, so they show `orders()` and `bids()` with parentheses. They are left as they were, because they record what was actually run.

`quote`, `last_price` and `ohlc` sit on `Instrument` rather than `TradeableInstrument`, because UBI quotes indices too, and an index's last price is one of the most used values. The order-book properties sit on `TradeableInstrument`, because an index has no order book.

The old `bids` and `asks` filtered out zero-price levels. UBI now drops empty levels itself, as `docs/architecture/contracts.md` in UBI states, so the filter is gone.

| Old | New | Notes |
|---|---|---|
| `quote` property | `quote` on `Instrument` | Full unified quote dict |
| `ltp` | `last_price` on `Instrument` | Uses `/api/instruments/ltp` |
| `ohlc` | `ohlc` on `Instrument` | Uses `/api/instruments/ohlc`; `ohlc` has no close, but the dict has `previous_close` |
| `bids`, `asks` | `bids`, `asks` | From `depth.buy` and `depth.sell` |
| `best_bid`, `best_offer`, `bid_offer_spread`, `mid_price` | Same names | |
| `vwap` | `volume_weighted_average_price` | UBI's `average_price` |
| `last_traded_quantity` | `last_quantity` | Underlying units, not lots |
| `total_traded_volume` | `total_traded_volume` | UBI's `volume` |
| `last_traded_at` | `last_trade_time` | Epoch seconds turned into an India-time `datetime` |
| none | `open_interest` | New; UBI's `oi` |
| `upper_circuit`, `lower_circuit`, `total_traded_value` | dropped | UBI no longer provides them |

## prices

`prices` renames UBI's `time` column to `datetime`, as the old frame had it, and converts it from UTC to India time. A daily candle therefore reads `2026-09-09 00:00:00+05:30` rather than `2026-09-08 18:30:00+00:00`. The frame keeps UBI's extra `oi` and `price_factor` columns. The `exchange`, `segment` and `interval` columns are inserted in front, as in the old code. The frame is sorted by time as a safeguard, because the adjusted-bars SQL function's ordering is not documented.

`adjusted` is sent as the text `true` or `false`, which UBI's `parse_bool` reads, rather than relying on how `requests` would print a Python bool.

## Finding instruments, and why search is not enough

`Instrument` gained four protected class methods on 2026-09-20, so that the equity classes could offer ways of finding contracts rather than only naming them: `_search_catalogue`, `_master_catalogue`, `_contracts_for` and `_expiry_dates`, with `_identity_frame` turning UBI's rows into a frame.

They sit on the base class because the mechanism is the same for every asset class, while the public calls belong to each class in its own file. That is the split the user's rules ask for: a shallow base holding what is genuinely identical, with each case's own surface visible where the case lives.

### Search finds a name, never a contract

UBI's `/api/instruments/search` ranks an exact symbol first, then symbols starting with the term, then symbols containing it, which is exactly right for finding a share. It is useless for a derivative, and measuring showed why. Asked for NIFTY index options on 2026-09-20 with the maximum limit of 200, it returned 200 rows that all shared one expiry, `2026-08-25`, which had passed four weeks earlier. The route sorts by expiry ascending, caps at 200 and takes no offset, so a segment with thousands of dead contracts hides every live one behind them permanently.

`/api/instruments/master` has no cap and streams the whole segment, and because UBI is on this machine it is quick:

| Segment | Rows | Time |
|---|---|---|
| `nse_equity_index_futures` | 23 | 0.0s |
| `nse_equity_index_options` | 14,826 | 0.2s |
| `nse_equity_options` | 125,967 | 1.3s |

So the rule is: `/search` for a name, `/master` for a contract. `_contracts_for` fetches the segment and narrows it here, because `/master` takes no filters of its own.

### Expired contracts, and what "live" means

A contract is live when its expiry is today or later, measured in India time through `INDIA_TIME_ZONE`, because a contract expiring today can still be traded until the close. The comparison is therefore `>=` rather than `>`. Expired contracts are dropped unless `include_expired` is True, which the user chose on 2026-09-20 over returning the universe as UBI holds it, since the first row of an unfiltered list is always a dead contract.

### Dates, and why every call fetches again

`_identity_frame` converts `expiry_date` to a `datetime.date` everywhere it appears, including inside the frames, so one rule covers the whole surface. Both a date and a `YYYY-MM-DD` string are accepted by the constructors either way.

Each discovery call fetches the segment master afresh, so asking for expiries and then a chain downloads it twice, about four seconds for single-stock options. That follows the standing rule against building caches around UBI, recorded under "No caching and no batching" above: a stale expiry list is a worse failure than a slow one, and if this ever matters the answer is a measurement rather than a cache added in advance.

## Tradeable or not

A segment ending in `_indices` is an index and cannot be traded; every other segment can. This is the old rule. It works on UBI's prefixed segment names too, such as `nse_equity_indices`. The check runs after the details are fetched, so a wrong class costs one request before it raises.

## The order surface

`TradeableInstrument` gained seven members on 2026-09-20: `place_order`, `modify_order`, `cancel_order`, `orders`, `trades`, and the `net_positions` and `day_positions` properties. They sit on `TradeableInstrument` rather than on `Instrument` because an index has no orders, no trades and no position. Holdings and funds were left out of this change, and holdings stay on `Equity` in `src/tradingmachine/assets/equities.py`, where they belong. (Since then the surface has grown: the property readers for each status, the price wrappers, the position methods, and on 2026-09-26 the references and synthetic objects described in the sections at the end of this note. Holdings later spread to four more classes, as the notes on `funds.py`, `mutual_funds.py` and `fixed_income.py` record.)

This is a fresh build against UBI's current contract, not a port. The old project's order methods were written against a much earlier UBI, and every name in them has since changed:

| Topic | Old code | UBI today |
|---|---|---|
| Order handle | An opaque encrypted `reference` | The broker's own `order_id`, plus an optional `broker` when two brokers share an id |
| Side | `side`, values `buy` and `sell` | `transaction_type`, values `BUY` and `SELL` |
| Product | `delivery`, `intraday`, `carry` | `CNC`, `MIS`, `NRML` |
| Order type | `market`, `limit`, `stop_loss`, `stop_loss_market` | `MARKET`, `LIMIT`, `SL`, `SL-M` |
| Filtering to one instrument | Matched `exchange` and `symbol` | Every row carries UBI's `instrument_id` |
| Positions | Never implemented | `/api/portfolio/positions`, with `net` and `day` buckets |

The old project also had sixteen convenience wrappers over `place_order`, such as `buy_at_market_price` and `buy_at_midprice`. The user decided on 2026-09-20 not to bring them across; a caller writes the `place_order` call itself. The user reversed that later the same day, and the wrappers were written after all, as the section "Naming the price instead of working it out" below records.

### Vocabulary is plain strings

`transaction_type`, `order_type`, `product` and `validity` are passed as plain strings, with no constants and no enum classes, which the user chose on 2026-09-20 over module constants and over a separate `src/tradingmachine/assets/orders.py`. UBI parses these fields case-insensitively and upper-cases them, so `"buy"` and `"limit"` reach the broker correctly, and UBI's own 400 is the single source of truth for what is allowed. This matches how `exchange`, `segment`, `option_type` and the candle `interval` are already handled.

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

`net_positions` and `day_positions` are properties rather than methods, which the user chose on 2026-09-20. At the time this was an exception, recorded under "Holdings, and why it is a property" in `.claude/notes/src/tradingmachine/assets/equities.py.md`, covering members that report what the account currently owns or owes while members reporting a market value stayed methods. On 2026-09-22 the market-value members became properties too, so the distinction is gone and the rule is now simply that a member which only reports a value is a property. Each read still sends a request, so code that needs the frame twice should bind it to a local variable.

### Order id, not instrument

`modify_order` and `cancel_order` take an `order_id` and send it straight through. They do not check that the order belongs to the instrument they were called on, which the user chose on 2026-09-20 over fetching the order book first to verify. UBI finds the order by id across the brokers' books, so the check would cost an extra request on every call and would only catch a caller using the wrong object. The wart to know about is that cancelling from the wrong instrument still works.

`dry_run` is exposed on all three writing methods. UBI builds the broker's request and returns it without sending, which is the only way to see the exact form UBI will post.

### No new exception classes

`src/tradingmachine/assets/exceptions.py` did not change on 2026-09-20. (`OrderError` was added later that day with the wrappers, and removed on 2026-09-26 when they moved onto price references; `PositionError` and `HoldingError` came with the position and holdings methods.) Because nothing is validated locally, there is no domain error to raise, and `src/tradingmachine/ubi_client/exceptions.py` already maps every status these routes return: 409 to `ConflictError`, 422 to `OrderRejectedError`, 429 to `RateLimitError` and 504 to `OrderOutcomeUnknownError`. Those four classes were added in September for exactly this, before any order method existed.

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

### Naming the price instead of working it out

Twenty-eight wrapper methods were added on 2026-09-20, on top of the order methods. Each one is a short call to `place_order` whose name says where the price comes from, so an intention such as "join the queue at the best bid" is one line rather than a calculation followed by an order.

| Family | Members | Price |
|---|---|---|
| Market | `buy_at_market_price`, `sell_at_market_price` | None; the market decides |
| Limit | `buy_at_limit_price`, `sell_at_limit_price` | The caller's |
| Top of the book | `buy_at_best_bid_price` and the three others | The first level of one side |
| Inside the spread | `buy_at_mid_price`, `sell_at_mid_price` | `mid_price` |
| The day's benchmark | `buy_at_volume_weighted_average_price` and its sell twin | `volume_weighted_average_price()` |
| Deeper in the book | Sixteen, by level and side | The second to fifth level of one side |

The sixteen deeper ones never existed in the old project, which left a comment saying they were mechanical repeats to be added on demand. The user asked for them on 2026-09-20, so they are written here for the first time.

The four that price at the top of the book carry a meaning that is easy to get backwards, and each docstring says which it is. Buying at the best bid is patient, because it joins the queue of buyers and waits; buying at the best offer is aggressive, because it crosses the spread and fills at once. Selling reverses that. The deeper levels extend the same idea: pricing further down your own side of the book makes an order more patient, and reaching further into the other side makes it more aggressive, because it can sweep several levels at once.

Three choices differ deliberately from the old project:

- **`product` is required, with no default.** The old project defaulted to `intraday` on these wrappers and to `delivery` on its holdings methods, so the same unstated word meant two different things depending on which method was called. That decides whether a buy becomes shares you keep or a position the broker closes before the session ends, which is too consequential to leave unsaid.
- **Every wrapper takes the same arguments.** In the old project only the two limit wrappers let you set `validity`, and the other ten silently used the default. Here all of them take `quantity`, `product`, `validity`, `after_market` and `tag`. Anything beyond that, such as a disclosed quantity or a stop loss, is a reason to call `place_order` directly.
- **They live in `instruments.py`** rather than in a mixin module of their own, which the user chose on 2026-09-20 over following the pattern that `src/tradingmachine/assets/analysis/` uses. The file grows to about 2,200 lines, and everything about orders stays in one place.

Two private helpers, `_bid_price_at` and `_offer_price_at`, originally read one level of one side through the existing `bids` and `asks` and raised `OrderError` when the book was not that deep. They were removed on 2026-09-26, as the next section explains.

#### Moved into UBI on 2026-09-26

UBI's order engine can now work a price out itself from a `price_reference`, and the commit that added it (`01aafb4` in the sibling project) names this class's wrappers as the reason: they "are not thirty-three order types. They are a side, a price reference and a quantity reference crossed with each other". The user decided that order types belong in UBI, so the wrappers kept their names and signatures and stopped reading the book. Each of the twenty-four book-based wrappers now sends `order_type` `limit`, no `price`, and a reference: `bid_level` or `offer_level` with `level` 1 to 5, `mid`, or `vwap`. The two market and two limit wrappers are unchanged and still send a plain price, so they work in either of UBI's placement modes, and the holdings members, which only call those four, are untouched.

Three things changed for a caller, and each is deliberate.

1. **The price is read when the order is sent, not when the method is called.** Before, the quote was read in one request and the order sent in another, so the price could already be stale. UBI reads the quote inside the engine, immediately before placing.
2. **The price is rounded to the tick.** A midpoint used to be sent exactly, so a one-tick spread produced a price between ticks that the exchange refused. UBI rounds towards the passive side, down for a buy and up for a sell, so a midpoint order never crosses the spread. The day's average price is rounded too.
3. **An empty or shallow book is UBI's 503.** `OrderError` existed only for the wrappers to raise when the book could not supply a price. Nothing in this package reads a price from the book any more, so the class was deleted, and the wrappers' docstrings name `ServiceUnavailableError` and `DirectPlacementError` instead.

Four wrappers were added at the same time, bringing the count to thirty-two: `buy_at_marketable_price` and `sell_at_marketable_price`, which send `{"kind": "marketable"}` with an optional `buffer_percent`, and `buy_at_last_price` and `sell_at_last_price`, which send `{"kind": "last"}`. They cover the two price kinds UBI offers that no wrapper named. The marketable pair matters most, because the Synthetic Order Atlas that UBI's engine was designed from lists "marketable limit" as one of the eight order types that need no class of their own, and it is what a market order has become in India: brokers convert API market orders to protected limit orders, and Flattrade's API refuses them outright. `buffer_percent` goes last in the signature so the five arguments every wrapper shares keep the same positions.

### Asking for orders by status

`orders` lost its `open_only` flag and gained a `status` argument on 2026-09-20, matched without regard to case, which covered all six of UBI's statuses including `EXPIRED`. Four named readers sat on top of it: `completed_orders`, `rejected_orders` and `cancelled_orders` were one-line calls to `orders`, and `open_orders` was not, because "open" is not a status. UBI reports an order still waiting in the market as `PENDING` at some brokers and `OPEN` at others, so `open_orders` filters on both through the existing `OPEN_ORDER_STATUSES` constant. That is also why the bulk cancel is called `cancel_open_orders` rather than the old project's `cancel_pending_orders`.

On 2026-09-22 the `status` argument was dropped, because `orders` became a property and a property takes no arguments. The user chose this over keeping `orders` as the one method among the readers and over adding `pending_orders` and `expired_orders` to cover the two statuses that lose their shortcut. `orders` now gives the whole book for this instrument, and the five readers each filter through the private `_orders_with_status`, which now takes one of `OPEN_ORDER_STATUSES`, `COMPLETED_ORDER_STATUSES`, `REJECTED_ORDER_STATUSES`, `CANCELLED_ORDER_STATUSES` or None. A caller wanting `PENDING` or `EXPIRED` on its own filters the `status` column of the frame, which is a single pandas expression and needs no extra request.

`cancel_open_orders` attempts every open order, naming the broker from each row so a shared order id cannot raise a `ConflictError`, and returns one row per order with `cancelled` and `error` columns. The old project stopped at the first failure, which both left the remaining orders open and lost the record of what had already been cancelled. It was the first place in the project to catch `UnifiedBrokerInterfaceError` itself; `liquidate_all_positions`, written later, does the same for the same reason. That is deliberate and is what the Google style guide allows a broad catch for: an isolation point where the error is recorded rather than swallowed.

### Acting on a position

Four members were added on 2026-09-20 so that a position can be changed and not only read: `add_to_position`, `reduce_position`, `liquidate_position` and `liquidate_all_positions`. Before them, closing a futures position meant reading `net_positions`, working out which way it pointed, taking its absolute size and flipping the side by hand, and getting that sign wrong doubles a position instead of closing it.

This is not a port. The old project had no position surface at all: the word `positions` does not appear in a single Python file in it, and its own notes list `/api/portfolio/positions` as unbuilt. The user believed on 2026-09-20 that it had `add_to_positions` and its siblings; what it actually had was `add_to_holdings`, `reduce_holdings` and `liquidate_holdings` on `ListedSecurity`, which are a different thing and were deferred to a separate `Equity` change, since made. Only the shape of the three was borrowed.

#### What a position is worth, and what it has made

`positions_value` and `positions_pnl` were added on 2026-09-20, after the four members above. They are properties, like `net_positions` itself and like `Equity.holdings`, because they report what the account holds rather than what the market is doing.

UBI prices a holding for you, giving it a `current_value`, but it does not price a position: a position row carries a signed `quantity` and a `last_price` and leaves the multiplication to the caller. `positions_value` does that multiplication and keeps the sign, which the user chose on 2026-09-20 over an unsigned figure and over the net cost of the position. A long position therefore adds and a short one subtracts, which is right, because a short position is an obligation to buy back rather than something owned.

When any position has no last price, the whole property returns None rather than a total quietly missing one of its parts. A number that silently omits a position is worse than no number.

`positions_pnl` returns UBI's whole `pnl` dict, with `realized`, `unrealized` and `total` added across every position, which the user chose over picking one of the three. The realised part is profit already booked by closing some of a position today; the unrealised part is what is still riding on what remains open. The total is computed from the two sums rather than by adding the rows' own totals, so it is rounded once instead of twice.

Both add up across products into a single answer, which the user chose over a frame with a row per product. That matches how the old project's `holdings_value` and `holdings_pnl` behaved.

One difference from the four members that change a position is deliberate and worth knowing: these two read `net_positions` directly rather than `_tradeable_positions`, so they count positions held under `margin_trading`, `cover` and `bracket` too. Those cannot be closed through UBI, but they are real money, and a total that left them out would be wrong.

#### Two vocabularies for one word

UBI reports a position's product with one set of words and accepts orders with another, so every one of these members has to translate, and the translation is not total.

| Order product, what `place_order` takes | Position product, what `net_positions` reports |
|---|---|
| `cnc` | `delivery` |
| `mis` | `intraday` |
| `nrml` | `carry` |
| nothing | `margin_trading`, `cover`, `bracket` |

The last three come from order kinds UBI's place route cannot send, so there is no order these methods could write to close such a position. The user chose on 2026-09-20 to ignore them entirely, which means a position held under `bracket` is invisible to the lookup, exactly as though it were not there.

That is a quiet trap, because a caller can hold a position and be told none exists. Every docstring says so in plain words, and `liquidate_all_positions` is deliberately different from the rest: it reads the unfiltered `net_positions` and reports an untradeable row as ignored, with the reason, rather than passing over it in silence. `_tradeable_positions` is the single place the filtering happens.

Two module constants hold the mapping, one per direction, because both directions are needed: a caller names a product in the order vocabulary, and the rows come back in the position vocabulary.

#### Which position, and which way

`product` is optional on all of them and names the order product. With one position held it is not needed; with several, leaving it out raises and the message lists what is actually held, which the user chose over making it always required.

Direction is never asked for when it can be worked out. `add_to_position` follows the position you hold, buying to add to a long one and selling to add to a short one. `reduce_position` does the opposite. `transaction_type` exists on `add_to_position` only for the case where nothing is held yet, and then `product` is required too, because neither can be read from a position that does not exist.

A `transaction_type` that contradicts the position held raises and points at `reduce_position`, which the user chose over silently following the position. Selling against a long position is reducing it, so a call that says otherwise is a mistake worth stopping rather than reinterpreting.

`reduce_position` refuses a quantity larger than the position, naming both figures. This is not the same as the rule against validating locally what UBI validates: UBI would accept the order happily and leave the account with a new position the other way round, which is not what the method was asked to do.

#### Pricing, and what gets reused

`price` is optional everywhere. Given, it sends a limit order; left out, it sends a market order, which is what closing a position usually means. This is the old holdings methods' convention, and the user confirmed it on 2026-09-20.

The four members place nothing themselves. `_place_to_change_position` picks among `buy_at_market_price`, `sell_at_market_price`, `buy_at_limit_price` and `sell_at_limit_price`, which finally gives the two market wrappers a caller inside the project.

### The first real order, and the two things it taught

The user ran the live script at 12:27 on Sunday 2026-09-20, with the market closed. It placed a genuine limit buy of one KWIL share at 28.85 against a last price of 41.22. UBI routed it to `wisdom_capital`, which answered `API Order Id sent` with order id `1310900080`, and UBI reported `outcome: accepted`. The modify that followed raised `NotFoundError: no broker order book in Redis holds this order_id`, and so did the cancel in the `finally` block, so the run ended in a traceback with what looked like an uncancelled order.

Reading the order book a few minutes later showed there was nothing to cancel. The order was already `REJECTED`, with `status_message` reading `OEMS:Target Exchange Adapter Is Not Connected To Exchange.`, and nothing was bought.

**An accepted order is not a live order.** UBI's `outcome: accepted` means the broker's own API took the request. The exchange sits behind that and can still refuse, which is exactly what an ordinary order meets on a closed market. Neither this class nor UBI checks the market's hours, despite what UBI's REST guide says about a 400 for out-of-hours orders; the order went through to the broker untouched. The order's real fate is read from `orders`, never from the answer `place_order` gave. Both facts are now in the `place_order` docstring.

**A freshly placed order cannot be modified or cancelled straight away.** UBI does not ask the broker about one order; it reads a copy of each broker's order book that its own collectors refresh every few seconds, and `modify` and `cancel` look the id up in that copy. The order placed at 12:27:14 was not there when the modify ran a fraction of a second later, which is what the 404 meant. It was there by the next reading. So the sequence to follow is place, wait for the id to appear in `orders`, then modify or cancel. Both docstrings now say so.

Nothing about this changes the class. Adding a wait or a retry inside `modify_order` would be the same mistake as adding a cache: it would hide UBI's own timing behind a guess about it. The waiting belongs in the caller, and the check script now polls `orders` for up to sixty seconds before it touches the order.

The script was changed in one other way. It now sends the order with `after_market=True` rather than only falling back to that after a 400 that never comes. An after-market order is queued by the broker rather than passed to the exchange, so it survives on a closed market and can actually be modified and cancelled, which is the whole point of the run.

### The order that worked, at 12:35 the same day

The third run went through the whole life of an order. It is the first proof that the writing methods work.

| Step | What happened |
|---|---|
| Place | `indmoney` took the after-market limit buy of one KWIL share at 28.85, as order `EQ-100659431`, answering `O-PENDING` |
| Appear | The order showed up in UBI's order book 2.0 seconds later, with status `PENDING` |
| Modify | The price changed from 28.85 to 26.79, with `status_before_modify: PENDING` |
| Read back | `orders()` showed the row at 26.79, so the change had really reached the broker |
| Cancel | The broker answered `CANCELLED`, with `status_before_cancel: PENDING` |
| Read back | `orders()` showed the row as `CANCELLED`, so nothing was left open |

The second run, between the two, had failed with `OrderRejectedError`, which is UBI's HTTP 422 and means the broker refused and nothing was placed. Its cause was never identified, because the script printed only the exception's message, and for a 422 UBI returns the broker's own answer rather than an `{"error": ...}` body, so the message falls back to `UBI returned HTTP 422` and the explanation sits in `detail`. The lesson for anyone reading a 422 is to read `detail`, not the message.

That failure also showed why a single attempt proves little. UBI's round-robin selector picks a different broker on every request, so one broker's refusal says nothing about the next, and two brokers, `fyers` and `groww`, take no after-market orders at all and are skipped with a reason. The check script now tries up to six times, prints each refusal in full, and stops at the first broker that takes the order. It never retries a 504, because an unknown outcome may have left a real order behind.

One small thing to know when reading the returned frames: a field that is null for every row of a numeric column comes back from pandas as `NaN` rather than `None`, which is why the pending order's `status_message` printed as `nan`.

The 2.0 second delay before the order appeared is the same lag the second run's `NotFoundError` was caused by, now measured rather than inferred.

## The wrappers, checked on 2026-09-20

The readers were checked against the live order book, which by then held five orders in KWIL. `orders()` returned all five, `orders(status="cancelled")` and `cancelled_orders()` both returned the same two, `orders(status="rejected")` and `rejected_orders()` both returned the same three, and `completed_orders()`, `open_orders()` and `orders(status="expired")` all returned None. `cancel_open_orders()` returned None, because nothing was open.

All twenty-eight wrappers were then checked offline, by replacing `place_order` on the instrument with a recorder and giving the instrument a made-up five-level book priced from 100.0 down to 96.0. Every wrapper sent the right side, the right order type and the right price: the market pair sent no price at all, the limit pair sent the caller's, the best-level four sent 100.0, and the deeper twelve sent 99.0, 98.0, 97.0 and 96.0 by level. The same twenty-eight were then called again with an empty book and no mid or average price, and all twenty-four that need a price raised `OrderError` while the four that do not were skipped. Nothing was sent in either pass.

### A check that placed real orders by accident

The first version of that check was wrong in a way worth recording. It called each priced wrapper for real, expecting `OrderError`, on the reasoning that the market was closed and the book would therefore be empty. The buy side was empty; the sell side was not. Two real orders went out, a `kotak` buy and a `shoonya` sell, and a third came back as HTTP 504 with its outcome unknown.

It ended safely. Both orders were rejected, by `Adapter is Logged Off` and by a rule refusing to sell a share the account does not hold at that broker, the unknown one never appeared in the order book across two minutes of watching, and nothing filled. But that was luck, not design.

The rule it cost is simple: a script Claude runs itself must never call a method that can place an order, even when the call is expected to raise first, and market hours and an empty book are not a safeguard. The plumbing of an order-placing method is checked by replacing the method that sends the request with a recorder; anything that can genuinely reach a broker belongs in the script the user runs.

## The live check of the whole order surface, 2026-09-20 at 13:23

The user authorised real after-market orders for one share of KWIL, priced no higher than one per cent above the last traded price, to be cancelled afterwards. The run covered everything that could be reached that way.

The order book at the time was worth recording, because it shaped what could be tested: no bids at all, one offer of 6,878 shares at 41.22, no mid price, and a volume weighted average price of 40.54. The check worked out from that book which wrappers had no price to use, rather than assuming, and called only those. Twenty of the twenty-four raised `OrderError` and sent nothing. The other four were left alone, because each would have placed a real order at a price of its own choosing.

Four orders were then placed, each through a different wrapper, and UBI's round robin spread them over three brokers:

| Wrapper | Broker | Price | Status when it arrived |
|---|---|---|---|
| `buy_at_limit_price` | zerodha | 41.63 | `PENDING` |
| `sell_at_limit_price` | zerodha | 41.63 | `PENDING` |
| `buy_at_best_offer_price` | dhan | 41.22 | `PENDING` |
| `buy_at_volume_weighted_average_price` | flattrade | 40.54 | `OPEN` |

All four reached UBI's order book 6.0 seconds after being placed, which is the same lag measured earlier, now seen across three brokers at once.

### Why `open_orders` spans two statuses, proved rather than argued

That table is the important result. Four orders placed within a second of each other, in the same instrument, arrived as three `PENDING` and one `OPEN`. The status is the broker's own word for the same situation, not a stage an order passes through.

`orders(status="pending")` returned three rows and `orders(status="open")` returned one. Had `open_orders` been written as a single-status filter, as the first design sketch had it, it would have found one order out of four, and `cancel_open_orders` would have cancelled that one and silently left three live orders with two brokers over the weekend. The decision to make `open_orders` span both statuses was taken on reasoning; this run is the evidence for it.

### `cancel_open_orders` with real orders

It cancelled all four, across three brokers, and reported each:

```
           order_id    broker  cancelled error
      3252609207270      dhan       True  None
     26091900006009 flattrade       True  None
2101580428170272768   zerodha       True  None
2101580428463874048   zerodha       True  None
```

`open_orders()` then returned None and `cancelled_orders()` returned six rows, the four new ones and the two from earlier in the day. The safety net found nothing left, the whole account's trade count stayed at zero, and the KWIL holding of 146 shares was untouched.

### One refusal, from the broker rather than the code

`modify_order` on the dhan order was refused with HTTP 422, `OrderRejectedError`. The order was an after-market order, and dhan refused to change it. This is not a fault in `modify_order`, which had already been proved against an indmoney order earlier in the day; it is a broker declining a modification it does not support for that kind of order. The check printed only the exception's message, which for a 422 is the fallback text, so the broker's own words were again in `detail` rather than in the message.

### What is still untested against a broker

Four wrappers were deliberately not run, because each would have gone outside what the user authorised. `buy_at_market_price` and `sell_at_market_price` carry no price at all, and the authorisation set a price ceiling. `sell_at_best_offer_price` and `sell_at_volume_weighted_average_price` would have sold at 41.22 and 40.54, both below that ceiling and so more likely to fill than the orders that were allowed. All four are covered by the offline check.

`trades`, `net_positions` and `day_positions` have still only ever returned None. Seeing them with data needs an order that actually fills, which means genuinely buying or selling, and that has not been asked for.

## The position methods, checked on 2026-09-20

The account held no positions at all and the market was closed, so every case was set up offline, with `place_order` replaced by a recorder and `net_positions` replaced by made-up frames. That is not a weaker check here than it was for the wrappers: the whole value of these methods is the arithmetic on the position, and a recorder shows exactly which order each one would send.

| Position | Call | What it did |
|---|---|---|
| Long 100 carry | `add_to_position(50)` | buy 50 nrml at market |
| Short 65 carry | `add_to_position(35)` | sell 35 nrml at market |
| Long 100 carry | `add_to_position(50, transaction_type="sell")` | `PositionError`, pointing at `reduce_position` |
| None | `add_to_position(50, product="nrml", transaction_type="buy")` | buy 50 nrml at market |
| None | `add_to_position(50)` | `PositionError`, asking for both |
| Long 100 carry | `reduce_position(40)` | sell 40 nrml at market |
| Short 65 carry | `reduce_position(30)` | buy 30 nrml at market |
| Long 100 carry | `reduce_position(150)` | `PositionError` naming 100.0 and 150 |
| Short 65 carry | `liquidate_position()` | buy 65 nrml at market |
| Carry and intraday | `reduce_position(10)` | `PositionError` naming both products |
| Carry and intraday | `reduce_position(10, product="mis")` | sell 10 mis at market |
| Bracket only | `liquidate_position()` | `PositionError`, nothing UBI can trade |
| Long 100 carry | `liquidate_position(price=41.5)` | sell 100 nrml at 41.5, a limit order |

`liquidate_all_positions` over a short carry, a long intraday and a bracket position closed the first two and reported the third:

```
 product order_product  quantity  closed    order_id                                          error
   carry          nrml     -65.0    True  recorded-9                                            NaN
intraday           mis     100.0    True recorded-10                                            NaN
 bracket           NaN      25.0   False         NaN ignored: UBI cannot send a bracket order...
```

It sent a buy of 65 under nrml and a sell of 100 under mis, which is the right direction for each, and returned None when nothing was held.

Against the live UBI the lookup was exercised through `_tradeable_positions` and `_position_row` alone, which cannot place an order. Both reported correctly that nothing is held. The public members were deliberately not called live, because a position appearing between the check and the call would have turned a read into a real order, which is the rule that came out of the wrapper check earlier in the day.

Seeing these work against a real position needs an order that fills, which means genuinely buying something and carrying it until it is closed. That has not been asked for.

## The two position totals, checked on 2026-09-20

Checked offline against made-up position frames, since the account holds nothing.

| Positions | `positions_value` | `positions_pnl` |
|---|---|---|
| None | None | None |
| Long 100 carry at 41.22, realised 120, unrealised -35 | 4122.0 | realized 120.0, unrealized -35.0, total 85.0 |
| Short 65 carry at 41.22, unrealised 12.5 | -2679.3 | realized 0.0, unrealized 12.5, total 12.5 |
| All three of those plus a bracket position of 25 | 2473.2 | realized 125.0, unrealized -21.5, total 103.5 |
| Long 100 carry, and an intraday position with no last price | None | realized 120.0, unrealized -22.5, total 97.5 |

The last two rows are the ones worth reading twice. The bracket position is counted in both totals, although none of the four members that change a position can see it, because it is real money. And a missing last price makes the value None while leaving the profit intact, which is right: the profit figures come from UBI and do not depend on a price this project has to supply.

Against the live account, which holds no position, both returned None.

## The properties, checked on 2026-09-22

Every converted member was read once against the live UBI, through `Equity(exchange="nse", symbol="INFY")` and `EquityIndex(exchange="nse", symbol="NIFTY")`, about an hour before the market opened. Nothing in the check could place an order.

| Property | What came back |
|---|---|
| `last_price` | 1038.5 |
| `ohlc` | `{'high': 1044.5, 'low': 1030.3, 'open': 1031.8}` |
| `quote` | The full dict, beginning `average_price`, `broker`, `broker_token`, `buy_quantity`, `change` |
| `bids`, `asks`, `best_bid`, `best_offer` | Five levels a side, best bid 1142.3 and best offer 934.7 |
| `bid_offer_spread` | -207.6 |
| `mid_price` | 1038.5 |
| `volume_weighted_average_price`, `open_interest` | None, which is right for a share before the open |
| `last_quantity`, `total_traded_volume` | 1 and 27,793 |
| `last_trade_time` | `2026-09-21 15:59:42+05:30` |
| `orders`, `open_orders`, `completed_orders`, `rejected_orders`, `cancelled_orders`, `trades`, `net_positions` | None, because the account had nothing that day |
| `EquityIndex.last_price` | 23411.45 |
| `EquityIndex.ohlc` | `{'high': None, 'low': None, 'open': None}` |

The crossed book, where the best bid sits 207.6 above the best offer, is UBI serving a stale pre-open depth rather than anything this refactor caused. It is worth knowing that `bid_offer_spread` and `mid_price` will happily return a negative spread, because neither checks the book for sense.

The five order and trade readers could only be shown to return None, since the account held no order that day. The path through `_orders_with_status` was exercised for each of the four status constants and for None, so the wiring is proved even though the filtering is not. The filtering itself was proved on 2026-09-20 against a book of five KWIL orders, recorded above, and the only thing that changed since is how the statuses reach `_orders_with_status`.

`prices(days=5)` was read in the same run and returned candles, which confirms that the one member left as a method still works from the same object.

## UBI's order engine, and what `place_order` gained on 2026-09-26

On 2026-09-23 UBI gained an order engine, a separate process that places orders on the REST API's behalf and can keep working an order after the request has been answered. With it, `POST /api/orders/place` reads three new optional objects: `price_reference`, which describes a price for UBI to work out from the live quote; `quantity_reference`, which describes a quantity for UBI to work out from the positions; and `synthetic`, which turns the order into one of forty-two order types such as a bracket or a trailing stop. The user decided that order types belong in UBI rather than here, so tradingmachine now passes these objects through instead of computing prices and quantities itself.

`place_order` takes the three as its last arguments, after `dry_run`, so every existing positional caller keeps working. `quantity` became `int | None` and is omitted from the body when it is None, like the other optional fields, because a quantity reference that liquidates a position supplies the quantity itself. It stays in its position in the signature and has no default, so a caller who wants no quantity has to say so.

### Why there is a check for engine mode, and how it works

In direct mode, which is UBI's default, the route checks the three objects' shapes and then ignores them. UBI's own documentation says so directly: a `LIMIT` order carrying only a `price_reference` is built with a price of 0, an order carrying only a `quantity_reference` is built with a quantity of 0, and a bracket or an iceberg is silently placed as one plain order. None of these is refused. The user's UBI runs in engine mode today, but a UBI restarted without its `.env`, or run on another machine, would fall back to direct mode without any sign, and the first order after that would be wrong in a way that costs money.

UBI has no route that reports its mode. What engine mode does do is add an `intent_id` to every answer, including dry runs and the engine's own refusals, because `IntentHandoff.engine_answer` writes it into every body; direct mode never adds one. The handoff happens before UBI reads `dry_run`, so a dry run goes through the engine too. That makes a dry run a reliable, free probe.

So when a live order carries any of the three objects and the client does not already know it is talking to an engine, `_probe_placement_mode` sends the same body once with `dry_run` set to True:

1. An answer carrying `intent_id` sets `placement_mode` to `engine` on the shared client, and the real order is then sent.
2. An answer without one sets it to `direct` and raises `DirectPlacementError`, so nothing live goes out.
3. A refusal is re-raised, because the real order would have been refused the same way. When the refusal's body carries an `intent_id` the mode is recorded as `engine` first. A 400 for a malformed body comes from validation that runs before the handoff and has no `intent_id`, so the mode stays unknown.

After every live order carrying one of the objects, `_record_placement_mode` looks at the answer again. An answer without an `intent_id` means UBI was switched to direct mode after the probe, and the order has already gone out as a plain order, so it records `direct` and raises `DirectPlacementError` with a message saying the order was sent and the order book should be read. That is the backstop; it cannot undo the order, but it stops the caller carrying on as if a bracket were protecting a position.

A dry run that carries one of the objects is not probed first, because it is itself the probe: it is sent once and then checked the same way, and an answer without `intent_id` raises rather than returning a request that would behave differently from what the caller asked for.

The mode is stored on the client rather than on the instrument because every instrument shares one client and the mode belongs to the server. The probe therefore costs one dry run per client, not one per order. A plain order with none of the three objects never probes, never checks and works in either mode, which keeps every order that worked before 2026-09-23 exactly as it was.

The cleaner fix would be one field on an authenticated UBI route that reports the mode, which would turn the probe into a single cached read. That belongs to the sibling project and is recorded in this project's former Known issues page, which the documentation rebuild of 2026-09-26 removed and which `git show b5761c0:docs/contributing/known-issues.md` still prints.

## The position methods moved onto quantity references on 2026-09-26

UBI's order engine resolves a `quantity_reference` from the positions when it sends the order. `reduce_position` sends `min(quantity, held)` and chooses the side that closes; `liquidate_position` sends the whole net position and chooses the side; both answer HTTP 409 when nothing is held under the product. The source is `../unified_broker_interface/docs/rest-api/price-quantity-references.md`. Following the user's decision that order behaviour belongs in UBI, `reduce_position` and `liquidate_position` now send one order carrying the reference instead of reading the position and working the direction out here.

`_place_to_close_position` is the shared mechanism, and it keeps one local read. A reference without a `product` makes UBI add every product's position together, which would not match the order's own `product` field, so when the caller names no product the positions are still read once here to find the only one held. That keeps the old `PositionError` for "several are held and none was named", which is a mistake the caller should hear about rather than one UBI should guess at. When a product is named, nothing is read here at all, and a product that is not held comes back as `ConflictError` from UBI's 409 rather than as a `PositionError`. That is a change for a caller who caught `PositionError`, recorded on the Positions page of the Python API tab, `docs/python-api/positions.md`.

The body carries `transaction_type` `sell` as a placeholder, because the route requires a side before the engine sees the reference, and the engine replaces it. It also carries `synthetic` `{"type": "simple", "closes_position": true}`. `simple` is the plain order type the engine runs anyway when no `synthetic` object is sent, so the order is unchanged; `closes_position` tells the engine the order is an exit, so it may use the share of a broker's daily order cap kept for exits (`UNIFIED_BROKER_INTERFACE_API_ORDER_DAILY_CAP_EXIT_RESERVE`). Without it, a day that had used its cap on entries could not close its positions through these methods, which is the one day closing matters most.

One behaviour changed on purpose. A reduction larger than the position used to be refused with `PositionError`, because sending it would have opened a position the other way round. UBI caps it at what is held, so it now closes the whole position, which is the outcome the old refusal was protecting. The refusal had no other purpose, so it was not kept.

`add_to_position` is unchanged. UBI's `add_to_position` kind is documented as the same as `absolute`: it does not read the position, so it cannot work out the direction, and the local logic is still what does the work. `_place_to_change_position` and `_open_a_new_position` now serve only it.

`liquidate_all_positions` still reads `net_positions` once, because it must report the `margin_trading`, `cover` and `bracket` positions as ignored, and then calls `liquidate_position` with each tradeable product named, so each close is one request and reads nothing further here. It still catches `PositionError` alongside `UnifiedBrokerInterfaceError`, because an unrecognised product can still raise it. It deliberately does not call UBI's `POST /api/orders/flatten`, which the user chose on 2026-09-26: flatten cancels every open order and closes every position in the whole account, which is a different request from closing this instrument's positions. It lives on `tradingmachine.accounts.account.Account` instead.

The accessor was named `_get_shared_unified_broker_interface` and private until 2026-09-26, when `tradingmachine.accounts.account.Account` needed the same client for `POST /api/orders/flatten`. An `Account` with a client of its own would connect separately and log every instrument out, so it had to share this one, and the method was made public as `shared_unified_broker_interface` rather than reached into from another module.

### The dry runs against the real UBI on 2026-09-26

Every order kind was sent to the real UBI as a dry run on 2026-09-26, a Saturday, through a scratchpad client that refused any request that was not a dry run to `/api/orders/place` or `/api/orders/flatten`, and refused every modify and cancel. No order was sent. The wrappers and position methods have no `dry_run` argument, so they were checked only offline, against a recording client, as the rule in "A check that placed real orders by accident" requires; that offline check passed 136 of 136 assertions, including every one of the forty-two classes' `synthetic` object against the JSON example for its type in UBI's glossary.

Every dry run that went through the engine, which in engine mode is every placement, came back as HTTP 504 with an `intent_id` and the message "the order engine did not answer within 5.0 seconds, so this order may still be placed". UBI's `.env` sets `UNIFIED_BROKER_INTERFACE_API_ORDER_PLACEMENT=engine`, but the engine's own service, `unified-orders@order_engine.service`, was inactive and disabled, so the API handed every order to a process that was not there. The flatten dry run, which does not go through the engine, answered normally. The queued dry runs are harmless: they are dry runs, and the engine refuses any intent it reads more than 30 seconds after the caller stopped waiting.

Two things were fixed from that run. The error's message had read only "UBI returned HTTP 504", which the client now takes from `status_message`. And a refusal carrying an `intent_id` on the main send, not only on the probe, now records `engine` as the placement mode, through `_record_engine_refusal`, which both paths share.

Whether UBI accepts each class's settings, rather than only their shape matching its glossary, therefore still has to be checked with dry runs once the engine is running.

## `prices_document` and `additional_details`, added on 2026-09-26

`prices` now fetches through `prices_document`, which returns UBI's whole answer as a `tradingmachine.ubi_client.prices_document.PricesDocument`, and builds its DataFrame with `PricesDocument.frame`. The frame is identical to the one `prices` built before; `.claude/notes/src/tradingmachine/ubi_client/prices_document.py.md` records the check. `prices_document` is public for callers that also need UBI's facts about the candles: the price basis, whether the instrument is adjustable, whether they came from UBI's cache or database, and the range read.

`additional_details` is a property that reads `/api/instruments/additional_details`, the extra attributes each broker publishes, such as the ISIN. It is read on every access, like `quote`.

Both go through `tradingmachine.ubi_client.instrument_catalogue.InstrumentCatalogue`, which does the same by instrument id for callers that do not want to build an `Instrument`; see its note for why that class exists.
