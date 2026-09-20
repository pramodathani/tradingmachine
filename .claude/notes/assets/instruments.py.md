# assets/instruments.py

This module holds `Instrument`, `TradeableInstrument` and `NonTradeableInstrument`. They were ported on 2026-09-14 from `assets/instruments.py` in the old tradingmachine project at `/run/media/pramod/6959D90B1DAD7E59/backup_20260910/pramod/Downloads/tradingmachine-master/`. The other classes in that file (`HoldableInstrument`, `Futures`, `Option`, `ListedSecurity`, `UncategorisedInstrument`) and the order methods of `TradeableInstrument` were out of scope and are not ported yet.

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
