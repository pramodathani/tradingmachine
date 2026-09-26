# src/tradingmachine/assets/commodities.py

This module holds the six commodity classes: `Commodity`, `CommodityFutures`, `CommodityOption`, `CommodityIndex`, `CommodityIndexFutures` and `CommodityIndexOption`. They were ported on 2026-09-20 from `src/tradingmachine/assets/commodities.py` in the old tradingmachine project at `/run/media/pramod/6959D90B1DAD7E59/backup_20260910/pramod/Downloads/tradingmachine-master/`. Currencies, funds and mutual funds are still to come.

It is a copy of `src/tradingmachine/assets/fixed_income.py`, which is itself a copy of `src/tradingmachine/assets/equities.py`. No existing module was touched and nothing was factored out, which is the user's standing choice for this family of modules.

| Class | Base class | UBI segment | Shape | Constructor takes |
|---|---|---|---|---|
| `Commodity` | `TradeableInstrument` | `commodities` | security | `exchange`, `symbol` |
| `CommodityFutures` | `TradeableInstrument` | `commodity_futures` | future | `exchange`, `underlying_symbol`, `expiry_date` |
| `CommodityOption` | `TradeableInstrument` | `commodity_options` | option | those three plus `strike_price`, `option_type` |
| `CommodityIndex` | `NonTradeableInstrument` | `commodity_indices` | security | `exchange`, `symbol` |
| `CommodityIndexFutures` | `TradeableInstrument` | `commodity_index_futures` | future | `exchange`, `underlying_symbol`, `expiry_date` |
| `CommodityIndexOption` | `TradeableInstrument` | `commodity_index_options` | option | those three plus `strike_price`, `option_type` |

UBI carries commodities on three exchanges, `mcx`, `ncdex` and `nse`, and the indices and their derivatives on `mcx` and `ncdex` only. Symbols are readable tickers, `GOLD`, `CRUDEOIL`, `ALUMINIUM`, `MCXBULLDEX`, and a derivative's `underlying_symbol` matches its underlying's `symbol` exactly, so this family has none of fixed income's ISIN awkwardness.

The construction pattern, the required identity fields, the re-raised not-found error and the prefixed segment check all follow the earlier modules, and the reasoning is in `.claude/notes/src/tradingmachine/assets/equities.py.md` rather than repeated here.

## No holdings members, and why

Unlike `Equity` and `FixedIncome`, no class here has `holdings` or anything built on it. This is not a choice; UBI cannot report a commodity as a holding. `CASH_SEGMENTS` in its `stock_brokers/instruments/mapping/utilities/segments.py` lists only equities, exchange traded funds, investment trusts, mutual funds, fixed income and uncategorised, and `bin/unified/holdings` resolves a holding against nothing else, so a holding whose token names a commodity is filtered out and keeps the broker's own symbol with no instrument id.

Positions are a different matter and do cover this family, so the position members inherited from `instruments.TradeableInstrument` are meaningful here.

## Quantity is in quotation units and must be a whole number of lots

This is the most important thing about ordering in this family and the easiest to get wrong, because it differs from every module ported so far.

An equity or a bond order is a securities-market order, and its quantity is simply a count of shares or units. A commodity order is not, so UBI measures the quantity against the contract's size and refuses anything that is not an exact multiple:

```
buy_at_market_price(quantity=1)    on MCX GOLD  ->  HTTP 400
                                       quantity must be a whole number of lots of 100
buy_at_market_price(quantity=100)  on MCX GOLD  ->  one lot
```

The figure passed is in quotation units rather than lots, and UBI converts it to whatever each broker counts in before sending, so the same number works whichever broker takes the order. On the `ncdex` the quotation unit is tonnes, although prices are quoted in quintals.

UBI's own documentation records that these markets were opened on 2026-09-15 before any live order confirmed the rule, and that no live test has settled it: Zerodha answered that MCX is disabled for the account and Dhan recorded a quantity then rejected the order for funds. So the rule above is UBI's stated contract rather than something observed end to end, and this module does not check it locally, in keeping with the standing rule that quantities go to UBI exactly as given.

## Neither a commodity nor a commodity index can be ordered

`Commodity` is built on `TradeableInstrument`, because its segment does not end in `_indices`, so it inherits `place_order` and all thirty-two price wrappers. Every one of them will be refused, for two independent reasons found in UBI's source: no broker declares a cash market for the commodity asset class, so broker selection passes every broker over, and UBI's contract size check refuses any non-securities order whose shape is not a future or an option. The rows in `commodities` are the exchange's underlying reference records, reached through Stoxkart's `SPOT` instrument type and Kotak's `COM` and `UNDCOM` types, not tradeable spot contracts.

`CommodityIndex` cannot be traded either, by the ordinary rule that an `_indices` segment is a `NonTradeableInstrument`, and UBI agrees: the indices are absent from its tradeable segment table altogether.

The class docstrings say this, so that a caller does not discover it by sending an order.

## An order can be refused for a reason that is not about the order

UBI decides each contract's size once every morning from the exchanges' own fields rather than from brokers' lot sizes, because the broker majority rule gave wrong answers here, notably a lot of 1 for NSE USDINR. When the sources disagree the contract is marked `conflict` and cannot be traded that day at all. UBI answers HTTP 503 with a `contract_size_status` of `conflict`, `undecided`, `no_source` or `single_source`.

A 503 from an order in this family therefore means UBI does not trust the contract's size today, not that UBI is unavailable. On 2026-09-15 twelve SILVER100 futures were in that state. `bse` currency and `ncdex` commodity contracts trade on a single source, Stoxkart alone.

## Quotes and candles

A commodity and a commodity index have no quote. Every broker's tick normaliser maps the MCX, NCDEX and NSE commodity venue codes to the derivative family, and a token is only kept among the segments that family allows, so a tick for a `commodities` or `commodity_indices` row can never resolve. `quote`, `last_price`, `ohlc` and the order-book values therefore raise `ServiceUnavailableError` for those two classes. The reason differs from fixed income's, where the problem is that no quote-serving broker carries the instrument at all.

The four derivative classes are quoted normally and, unlike anything else ported so far outside equities, **they have candles**. This was measured rather than inferred, and it matters because it is the first time the roughly 192 inherited analysis methods have data to work on outside the equity family.

It also contradicts UBI's own source comment in `historical/utilities/unified/sources.py`, which says "No derivative bars are stored yet, so this is policy only". That comment is stale. The measurement below is what to trust.

One more quirk worth knowing: MCX and NCDEX derivatives are the only instruments in UBI allowed a negative price, which matters for spread contracts.

## What was deliberately not added

UBI has no commodity market on `bse`, and only Stoxkart and Wisdom Capital can take an NCDEX order. It would be easy to reject those in the constructors. That was not done, because this project passes vocabulary UBI validates straight through, and a lookup UBI has no rows for already raises the class's own error by the ordinary not-found path. Checking locally would duplicate UBI and drift from it.

## Verified on 2026-09-20

A live check against UBI on `127.0.0.1:8080`, from a scratchpad script. All six classes resolved with the expected segment and shape. **No order was sent**, and this module has no method that could send one without being asked to.

| Class | Contract | Segment | `lot_size` | `tick_size` | Brokers | `last_price` | Candles |
|---|---|---|---|---|---|---|---|
| `Commodity` | mcx GOLD | `mcx_commodities` | 1 | 100 | 3 | no quote | None |
| `CommodityFutures` | GOLD 2026-10-05 | `mcx_commodity_futures` | 100 | 1 | 9 | 154263.0 | 40 |
| `CommodityOption` | GOLD 2026-09-25 173500 CE | `mcx_commodity_options` | 100 | 0.5 | 9 | 0.5 | 40 |
| `CommodityIndex` | mcx MCXBULLDEX | `mcx_commodity_indices` | 1 | 0.05 | 4 | no quote | None |
| `CommodityIndexFutures` | MCXBULLDEX 2026-09-25 | `mcx_commodity_index_futures` | 30 | 1 | 9 | 34837.0 | 40 |
| `CommodityIndexOption` | MCXBULLDEX 2026-09-25 34900 CE | `mcx_commodity_index_options` | 30 | 0.05 | 8 | 154.15 | 40 |

The other two exchanges resolved as well: `ncdex` GUARSEED10 into `ncdex_commodities` and `nse` ALUMINIUM into `nse_commodities`, both with a lot size of 1.

The GOLD futures lot size of 100 is Groww's figure, chosen by UBI's rule that Groww is the lot authority on MCX; the other eight brokers say 1, and the note on `src/tradingmachine/assets/instruments.py` records why Groww's is right. The tick sizes of the two security-shape rows, 100 for MCX GOLD and 100 for the NCDEX commodity, are raw broker values that UBI does not convert for these segments, so they are much less trustworthy than a derivative's.

No class has a `holdings` attribute, `CommodityIndex` has no order-book methods and `CommodityFutures` does, which is the split the base classes intend.

The analysis methods work, which is the headline. `relative_strength_index(window=14, days=90)` on the MCX gold future returned 61 rows:

```
                 datetime    close    rsi_14
2026-09-14 00:00:00+05:30 151230.0 44.259329
2026-09-15 00:00:00+05:30 150809.0 43.351621
2026-09-16 00:00:00+05:30 152470.0 47.892248
```

Discovery, live:

| Call | Result |
|---|---|
| `Commodity.search(exchange="mcx", term="GOLD")` | 34 rows: `GOLD`, `GOLDAHM`, `GOLDDEL`, `GOLDGLOBAL`, `GOLDGUINEA`, … |
| `CommodityIndex.search(exchange="mcx", term="DEX")` | 13 rows, the whole MCX index family from `MCXALUMDEX` to `MCXZINCDEX` |
| `CommodityFutures.expiries(underlying_symbol="GOLD")` | 2026-10-05, 2026-12-04, 2027-02-05, 2027-04-05 |
| `CommodityOption.expiries(underlying_symbol="GOLD")` | 2026-09-25, 2026-10-30, 2026-11-27, 2026-12-31 |
| `CommodityOption.strikes` and `chain` for 2026-09-25 | 1,074 strikes and 2,148 rows |
| `CommodityIndexFutures.expiries(underlying_symbol="MCXBULLDEX")` | 2026-09-25, 2026-10-28, 2026-11-27, 2026-12-30 |
| `CommodityIndexFutures.contracts(exchange="mcx")` | 8 rows |
| `CommodityIndexOption.strikes` | 118 strikes |

The check that matters passed: the row in the middle of the gold chain, `GOLD 2026-09-25 173500.0 CE`, rebuilt into a `CommodityOption` and UBI returned the same `instrument_id`, `a13c491a-da06-5f31-b4f4-13cde7f36bc6`.

Every error fired with the original `InstrumentError` as its `__cause__` and was catchable as `InstrumentError`:

| Case | Error raised |
|---|---|
| an unknown commodity symbol | `CommodityError` |
| an index asked for as a commodity | `CommodityError` |
| a commodity asked for as an index | `CommodityIndexError` |
| a futures contract with no such expiry | `CommodityFuturesError` |
| an option at an impossible strike | `CommodityOptionError` |
| an index future with no such expiry | `CommodityIndexFuturesError` |
| an index option at an impossible strike | `CommodityIndexOptionError` |
| a futures contract with no `expiry_date` | `TypeError`, before any request |
