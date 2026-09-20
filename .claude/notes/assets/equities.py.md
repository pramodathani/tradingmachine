# assets/equities.py

This module holds the six equity-family classes: `Equity`, `EquityFutures`, `EquityOption`, `EquityIndex`, `EquityIndexFutures` and `EquityIndexOption`. They were ported on 2026-09-20 from `assets/equities.py` in the old tradingmachine project at `/run/media/pramod/6959D90B1DAD7E59/backup_20260910/pramod/Downloads/tradingmachine-master/`. The sibling asset classes in the old project, `commodities.py`, `currencies.py`, `fixed_income.py`, `funds.py` and `mutual_funds.py`, follow the same pattern and are not ported yet.

Each class exists so that the kind of contract is the class you pick rather than a segment name passed by hand, and so that the constructor asks for exactly the fields that identify one of its own contracts and refuses the rest. The old project's rationale was the same.

| Class | Base class | UBI segment | Shape | Constructor takes |
|---|---|---|---|---|
| `Equity` | `TradeableInstrument` | `equities` | security | `exchange`, `symbol` |
| `EquityFutures` | `TradeableInstrument` | `equity_futures` | future | `exchange`, `underlying_symbol`, `expiry_date` |
| `EquityOption` | `TradeableInstrument` | `equity_options` | option | `exchange`, `underlying_symbol`, `expiry_date`, `strike_price`, `option_type` |
| `EquityIndex` | `NonTradeableInstrument` | `equity_indices` | security | `exchange`, `symbol` |
| `EquityIndexFutures` | `TradeableInstrument` | `equity_index_futures` | future | `exchange`, `underlying_symbol`, `expiry_date` |
| `EquityIndexOption` | `TradeableInstrument` | `equity_index_options` | option | `exchange`, `underlying_symbol`, `expiry_date`, `strike_price`, `option_type` |

The segment names match UBI's own `CANONICAL_SEGMENTS` in `stock_brokers/instruments/mapping/utilities/segments.py`. `equity_indices` has shape `security` in UBI, like any cash instrument, and is non-tradeable only because its name ends in `_indices`, which is the rule `instruments.py` already applies.

## What changed from the old code

| Topic | Old code | Now |
|---|---|---|
| Base classes | `ListedSecurity`, `Futures` and `Option`, which the current port does not have | `TradeableInstrument` and `NonTradeableInstrument` directly, as the user decided on 2026-09-20 |
| `id` argument | Every class accepted one, expanded by `expand_short_id` | Dropped; only the identity fields are accepted |
| Identity arguments | All defaulted to `None` | All required, with no default |
| Exception names | `EquityException` and five subclasses of it | `EquityError` and five siblings, all flat under `InstrumentError` |
| Segment check | `self.segment != "equities"` against a bare name | Against the exchange-prefixed name UBI returns |
| Not-found error | Left as the general `InstrumentException` | Re-raised as the class's own error, chained |

## Why the identity arguments are required

The old classes defaulted every identity argument to `None` because they also accepted an `id`, so no one field was compulsory. With `instrument_id` gone, there is always exactly one right set of arguments, and making them required means Python raises `TypeError` at the call site. Otherwise the `None` would simply be dropped from the query string by `Instrument._fetch_details` and UBI would answer HTTP 400 a round trip later. The live check confirmed the message: `EquityFutures.__init__() missing 1 required positional argument: 'expiry_date'`.

## Why the not-found error is re-raised

`Instrument._fetch_details` turns UBI's 404 into a general `InstrumentError` whose message quotes the query parameters. That says nothing about which kind of contract was asked for, and it means `except EquityOptionError` would never catch anything, because the six classes could otherwise only fail on the segment check, which cannot fire. Each constructor therefore catches `InstrumentError` around `super().__init__` and raises its own error with `from error`.

The wrapper message is self-contained and does not quote the original, which would read as two errors glued together. The chain carries UBI's own wording into the traceback, and the live check confirmed that `__cause__` is the original `InstrumentError` in every case.

Catching `InstrumentError` also catches its subclasses `TradeableInstrumentError` and `NonTradeableInstrumentError`. That is harmless here: those two fire only when a segment's index-ness disagrees with the base class, and each class hard-codes a segment that agrees with its base class, so neither can be raised.

## Why the segment check compares the whole prefixed name

UBI accepts a bare segment such as `equities` but always returns it exchange-prefixed, such as `nse_equities`, so the old code's `self.segment != "equities"` would now always be true. The check compares against `f"{self.exchange}_{EQUITY_SEGMENT}"`, built from the exchange UBI itself resolved, which is exact.

A suffix test with `endswith` would also work, because no two segments in UBI's vocabulary end the same way once the leading underscore is included, but that is a fact the next reader would have to re-derive from UBI's segment list. The full comparison needs no such reasoning.

The check cannot fire as the module stands. The segment is fixed by the class and `instrument_id` is not accepted, so UBI can only return the segment it was asked for. It is a guard against a future change in UBI rather than a live code path.

## Holdings, and why it is a property

`Equity` has a `holdings` property, added on 2026-09-20. It is the only class in the module that has one, because a share is the only thing here that can be held for the long term: a derivative is a position rather than a holding, and an index cannot be held at all.

It is a property rather than a method, which the user asked for and confirmed. That is a deliberate exception to the rule in `.claude/notes/assets/instruments.py.md` under "Live values are methods", where every value fetched from UBI is a method because each costs a network call. The old project exposed it as a property too. The cost to keep in mind is that a plain attribute access sends a request, so `if share.holdings and share.holdings["quantity"] > 10` fetches twice; code that needs the row more than once should bind it to a local variable.

UBI has no endpoint for one instrument's holding. `GET /api/portfolio/holdings` takes no parameters and returns the whole account, merged across all ten brokers and priced from `unified:quotes:live`, so the property fetches the document and finds its own row.

The row is matched by `instrument_id` first and by `symbol` second. The fallback is not defensive padding; it is required by how UBI merges. Its documentation states that holdings sharing an ISIN or an instrument id become one row, "whichever broker's arrives first", so a stock held on the nse at one broker and on the bse at another is filed under a single listing that may not be the one you asked for. Matching on the id alone would then report that you hold nothing while the shares are there. ISIN would be the better second key, but `/api/instruments/details` does not return an ISIN, so an `Equity` does not know its own.

## Why a derivative does not hold its underlying

The first plan had each futures and option contract build an object for its underlying share or index and keep it. The user removed that on 2026-09-20, and the module has no `underlying` attribute.

Beyond the extra request per contract, which would double the cost of building an option chain, UBI gives no reliable way to make the link. There is no foreign key and no `underlying_instrument_id`: a derivative is joined to its underlying only by its `underlying_symbol` string matching a cash or index instrument's `symbol`. For shares that holds, because NSE equity symbols have their series suffix stripped during mapping. For indices it rests on an alias table. `NSE_INDEX_ALIASES` in UBI's `stock_brokers/instruments/mapping/zerodha.py` normalises the published spellings onto the derivative's underlying symbol, so Kite's `NIFTY 50` index row is stored as `NIFTY` and `NIFTYBANK` as `BANKNIFTY`, covering `NIFTY`, `BANKNIFTY`, `FINNIFTY`, `MIDCPNIFTY` and `NIFTYNXT50`. `NIFTYFPI` is not in that table and falls back to a secondary master lookup, and the BSE indices rely on the published spelling already matching. A caller that wants the underlying builds it itself and can decide what to do when it is not there.

## Verified on 2026-09-20

A live check against UBI on `127.0.0.1:8080`, from a scratchpad script, built all six classes and confirmed every segment and shape.

| Class | Contract | Segment resolved | `lot_size` | `tick_size` | `last_price` |
|---|---|---|---|---|---|
| `Equity` | RELIANCE | `nse_equities` | 1 | 0.1 | 1226.4 |
| `EquityFutures` | RELIANCE 2026-09-29 | `nse_equity_futures` | 500 | 0.1 | 1242.0 |
| `EquityOption` | RELIANCE 2026-09-29 1250 CE | `nse_equity_options` | 500 | 0.05 | 11.95 |
| `EquityIndex` | NIFTY | `nse_equity_indices` | 1 | 0.05 | 23346.4 |
| `EquityIndexFutures` | NIFTY 2026-09-29 | `nse_equity_index_futures` | 65 | 0.1 | 23380.0 |
| `EquityIndexOption` | NIFTY 2026-09-29 23350 CE | `nse_equity_index_options` | 65 | 0.05 | 171.1 |

The inherited behaviour came through as expected. An `Equity` carries 192 analysis methods beyond what the instrument classes define, and `relative_strength_index(window=14, days=90)` returned 63 daily rows ending at 32.08. The order-book methods are present on the five tradeable classes and absent on `EquityIndex`, whose `last_price` still works, which is the split `instruments.py` intends.

Every error fired and was catchable as `InstrumentError`, each with the original `InstrumentError` as its `__cause__`:

| Case | Error raised |
|---|---|
| `Equity(exchange="nse", symbol="NOSUCHSHARE")` | `EquityError` |
| `Equity(exchange="nse", symbol="NIFTY")`, an index asked for as a share | `EquityError` |
| `EquityIndex(exchange="nse", symbol="RELIANCE")`, a share asked for as an index | `EquityIndexError` |
| `EquityOption` at strike 999999 | `EquityOptionError` |
| `EquityIndexFutures` expiring 2001-01-25 | `EquityIndexFuturesError` |
| `EquityFutures` with no `expiry_date` | `TypeError`, raised by Python before any request |

The `holdings` property was checked against the real account the same day, which happened to contain the merge case the symbol fallback exists for. Of the seven holdings, six were filed under `nse_equities` and were found by `instrument_id`. The seventh, VIJIFIN, was filed under `bse_equities` with instrument id `ce5c4445-1425-5009-b653-2ab06c968c43`, while `Equity(exchange="nse", symbol="VIJIFIN")` resolves to `792fcc3e-c47d-55c5-8149-fb226b0facb6`. The ids do not match, and only the symbol fallback found the row and its three shares. `Equity(exchange="nse", symbol="RELIANCE")`, which is not held, returned None, and `EquityIndex` has no `holdings` member at all.

Two things about the check script itself are worth recording, because the next person to verify this will hit them. UBI's `/api/instruments/search` orders its results by expiry ascending and has no offset parameter, so for a name with many contracts the 200-row limit returns only long-past expiries and never a live one. Live expiries were taken from the futures segments instead, which are small enough to return whole: `nse_equity_futures` holds 855 instruments and `nse_equity_index_futures` holds 23, against 125,967 in `nse_equity_options` and 14,826 in `nse_equity_index_options`. Equity options share the monthly expiry of the equity future on the same underlying, so that expiry works for both. A listed strike was then found by asking `/api/instruments/details` about round strikes outward from the spot price until one resolved.

The check also turned up a cosmetic fault in `Instrument.__repr__`, which belongs to `instruments.py` rather than to this module: it formatted every identity value with `str(value)!r`, so a strike price printed as `strike_price='1250.0'`, quoted as though it were text. That matters here because the segment-check messages embed `{self!r}`. It was fixed the same day, and the reasoning is in `.claude/notes/assets/instruments.py.md`.
