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

## Acting on a holding, and what it is worth

`holdings_value`, `holdings_pnl`, `add_to_holdings`, `reduce_holdings` and `liquidate_holdings` were added to `Equity` on 2026-09-20. They sit here rather than on `instruments.TradeableInstrument` for the reason `holdings` itself does: a derivative leaves a position rather than a holding, and an index cannot be held at all.

The three order methods take their shape from `ListedSecurity` in the old project. Nothing else carries over, because that project's order vocabulary has since changed completely and it ignored a field that costs a rejected order.

### UBI prices a holding but not a position

`holdings_value` reads `current_value` off the row. This is the opposite of `instruments.TradeableInstrument.positions_value`, which has to multiply a signed quantity by a last price, because UBI gives a holding a value and gives a position none.

`holdings_pnl` returns the row's `pnl` dict whole, as `positions_pnl` does, but the two dicts are not the same shape and the docstring says so. A holding reports `day_change`, `day_change_percentage` and `unrealized`; a position reports `realized`, `unrealized` and `total`. Only `unrealized` means the same thing in both. There is no realised figure for a holding, because selling a share removes it from the holding rather than booking a profit against it.

Both are properties, like `holdings`, and each sends its own request, so code that wants the value and the profit together should bind `holdings` to a local variable and read both fields from it rather than touching two properties.

### The product is fixed, not a parameter

Every order these three send is `cnc`. A holding is shares kept in the demat account, and `cnc` is the only product that buys into or sells out of one. The old project made this a parameter defaulting to `delivery`, and the user chose on 2026-09-20 to remove it.

The reason is worth stating plainly, because it is not a matter of taste. Selling a holding as `mis` does not sell your shares. It opens an intraday short position alongside them, which the broker squares off before the session ends, so the mistake costs money twice and leaves the holding untouched. Taking the argument away makes that impossible to do by accident.

### Pledged shares are not sellable

A holdings row carries `collateral_quantity`, the part pledged as margin, which a broker will not let you sell until it is released. The user chose on 2026-09-20 to have `reduce_holdings` and `liquidate_holdings` work on the free shares, which are `quantity` minus `collateral_quantity`, rather than on the whole holding and letting the broker refuse.

So `liquidate_holdings` sells what is free rather than everything, `reduce_holdings` refuses a quantity beyond it and names all three figures, and a holding that is entirely pledged raises rather than sending an order that cannot succeed.

Every `collateral_quantity` in the account was `0.0` on 2026-09-20, so this changes nothing today. It matters the first time anything is pledged, and until then it is invisible, which is exactly why it went in now rather than later.

`add_to_holdings` reads nothing before it buys. A share can be bought whether or not it is already held, and UBI checks funds no more than a broker's order endpoint does.

### One reading of the holdings, not two

The old project's `liquidate_holdings` called `reduce_holdings`, so it fetched the whole account's holdings twice and could decide on one figure and act on another. Here `_held_row` reads once, `_free_quantity` works out what can be sold, and `_sell_from_holdings` sends the order, so each method makes one request and one decision.

## Finding contracts you do not already know

Each of the six classes gained class methods on 2026-09-20 for finding instruments, over the mechanism in `instruments.py` described under "Finding instruments, and why search is not enough". The class supplies its own segment, exactly as its constructor does, so a segment string is never typed:

| Class | Calls |
|---|---|
| `Equity`, `EquityIndex` | `search` |
| `EquityFutures`, `EquityIndexFutures` | `expiries`, `contracts` |
| `EquityOption`, `EquityIndexOption` | `expiries`, `strikes`, `chain` |

The user chose class methods on these classes on 2026-09-20, over a separate catalogue class taking a segment argument and over having both. The cost is that each asset class ported later repeats the pattern; the gain is that the kind of contract stays the class rather than becoming a string again, which is the whole idea of this module.

### Rows, not objects

`search`, `contracts` and `chain` return a `pandas.DataFrame` of identities, never instrument objects. This is the user's decision from 2026-09-20 and it is about cost rather than taste: every constructor here looks its own contract up through `/api/instruments/details`, so returning a RELIANCE chain as objects would send 214 separate requests where returning rows sends none. The caller builds the two or three contracts it actually wants.

An identity row carries `instrument_id`, `exchange`, `segment`, `shape`, `symbol`, `underlying_symbol`, `expiry_date`, `strike_price` and `option_type`. It does not carry `lot_size`, `tick_size` or `carried_by`, which is the other reason not to return objects built from it: they would be missing attributes that every other instrument has.

`expiries` and `strikes` return plain lists rather than frames, because a single column of values is not a table.

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

## The holdings members, checked on 2026-09-20

`holdings_value` and `holdings_pnl` were checked against the real account, which is the first of these features that could be verified live without sending an order, because the account genuinely holds seven shares.

| Share | `holdings_value` | `holdings_pnl` | The raw row |
|---|---|---|---|
| KWIL | 6018.12 | day_change 1.31, day_change_percentage 3.28, unrealized -19.36 | `current_value` 6018.12, 146 shares, 0 pledged |
| ONGC | 698.4 | day_change 0.37, day_change_percentage 0.16, unrealized -13.45 | `current_value` 698.4, 3 shares, 0 pledged |
| RELIANCE | None | None | not held |

The three order methods were checked offline, with `place_order` replaced by a recorder and `holdings` by made-up rows, which is the only way to reach the pledged-collateral cases while the real account has nothing pledged.

| Holding | Call | What it did |
|---|---|---|
| 146, none pledged | `add_to_holdings(10)` | buy 10 cnc at market |
| 146, none pledged | `add_to_holdings(10, price=41.5)` | buy 10 cnc at 41.5 |
| Not held | `add_to_holdings(10)` | buy 10 cnc at market, no error |
| 146, none pledged | `reduce_holdings(50)` | sell 50 cnc at market |
| 146, none pledged | `reduce_holdings(200)` | `HoldingError`, 146 free, 200 asked |
| 146, 40 pledged | `reduce_holdings(120)` | `HoldingError`, 106 of 146 free |
| 146, 40 pledged | `reduce_holdings(100)` | sell 100 cnc at market |
| 146, none pledged | `liquidate_holdings()` | sell 146 cnc at market |
| 146, 40 pledged | `liquidate_holdings()` | sell 106 cnc at market |
| 146, all 146 pledged | `liquidate_holdings()` | `HoldingError`, none can be sold |
| 146, none pledged | `liquidate_holdings(price=41.5)` | sell 146 cnc at 41.5 |
| Not held | `reduce_holdings(10)` | `HoldingError`, not held |
| Not held | `liquidate_holdings()` | `HoldingError`, not held |

Eight orders were recorded and none was sent, and every one of them carried the product `cnc`, which is the point of taking that argument away.

No real order has been sent through any of the three. The authorisation the user gave earlier in the day covered a specific test of the order and wrapper methods, and it was not assumed to extend to these.

## The discovery calls, checked on 2026-09-20

Every call here reads the instrument catalogue and nothing else, so the whole check ran live against UBI with no order risk.

| Call | Result | Time |
|---|---|---|
| `Equity.search(term="RELI")` | RELIABLE, RELIANCE, RELIGARE, RELINFRA | 0.02s |
| `EquityIndex.search(term="NIFTY", limit=8)` | NIFTY and seven more index names | 0.00s |
| `Equity.search(term="ZZZNOSUCHTHING")` | None | 0.00s |
| `EquityFutures.expiries("RELIANCE")` | 2026-09-29, 2026-10-27, 2026-11-23 | 0.02s |
| the same with `include_expired=True` | those three, plus 2026-08-25 | 0.02s |
| `EquityIndexFutures.contracts("NIFTY")` | the three live quarterly contracts | 0.00s |
| `EquityOption.expiries("RELIANCE")` | the three live monthly expiries | 2.09s |
| `EquityOption.chain("RELIANCE", 2026-09-29)` | 214 contracts, first rows 620 CE and 620 PE | 2.20s |
| `EquityOption.strikes("RELIANCE", 2026-09-29)` | 107 strikes, 620.0 to 1920.0 | 2.10s |
| `EquityIndexOption.expiries("NIFTY")` | 18 live expiries, weekly then monthly | 0.24s |
| `EquityIndexOption.chain("NIFTY", 2026-09-22)` | 472 contracts | 0.27s |

The single-stock option calls cost about two seconds each, because each one downloads all 125,967 rows of `nse_equity_options` afresh. Index options cost a quarter of a second for 14,826 rows, and futures and equities are instant.

### The check that matters

A row was taken from the middle of the RELIANCE chain, RELIANCE 2026-09-29 1270.0 PE, and an `EquityOption` was built from its four identity fields. UBI returned the instrument id `12278f86-2feb-54b0-875f-4c1311d550fc`, which is the same id the row carried, and the object came back with a lot size of 500 and a tick size of 0.05.

That is the proof the whole feature rests on: discovery and construction agree on what an instrument is, so a row found by searching can be turned into a tradeable contract without guessing.
