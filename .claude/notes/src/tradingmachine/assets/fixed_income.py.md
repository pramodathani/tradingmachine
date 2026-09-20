# src/tradingmachine/assets/fixed_income.py

This module holds the six fixed income classes: `FixedIncome`, `FixedIncomeFutures`, `FixedIncomeOption`, `FixedIncomeIndex`, `FixedIncomeIndexFutures` and `FixedIncomeIndexOption`. They were ported on 2026-09-20 from `src/tradingmachine/assets/fixed_income.py` in the old tradingmachine project at `/run/media/pramod/6959D90B1DAD7E59/backup_20260910/pramod/Downloads/tradingmachine-master/`. The sibling asset classes in that project, `commodities.py`, `currencies.py`, `funds.py` and `mutual_funds.py`, follow the same pattern and are not ported yet.

The module is a copy of `src/tradingmachine/assets/equities.py` rather than a generalisation of it. The user chose this on 2026-09-20, having been offered the alternative of lifting the holdings mechanism onto a base class the way the discovery mechanism already sits on `Instrument`: reflect the equities implementation, and keep holdings inside `FixedIncome` alone. So `src/tradingmachine/assets/equities.py` was not touched, and the free-to-sell arithmetic now exists once per holdable asset class. Expect the same answer when exchange traded funds, investment trusts and mutual funds arrive.

| Class | Base class | UBI segment | Shape | Constructor takes |
|---|---|---|---|---|
| `FixedIncome` | `TradeableInstrument` | `fixed_income` | security | `exchange`, `symbol` |
| `FixedIncomeFutures` | `TradeableInstrument` | `fixed_income_futures` | future | `exchange`, `underlying_symbol`, `expiry_date` |
| `FixedIncomeOption` | `TradeableInstrument` | `fixed_income_options` | option | those three plus `strike_price`, `option_type` |
| `FixedIncomeIndex` | `NonTradeableInstrument` | `fixed_income_indices` | security | `exchange`, `symbol` |
| `FixedIncomeIndexFutures` | `TradeableInstrument` | `fixed_income_index_futures` | future | `exchange`, `underlying_symbol`, `expiry_date` |
| `FixedIncomeIndexOption` | `TradeableInstrument` | `fixed_income_index_options` | option | those three plus `strike_price`, `option_type` |

The segment names come from UBI's own `CANONICAL_SEGMENTS` in `stock_brokers/instruments/mapping/utilities/segments.py`. One is irregular: the cash segment is `fixed_income`, not pluralised, where the equity one is `equities`. It must not be tidied, because the string is baked into UBI's `CASH_SEGMENTS`, its Redis cache keys and the `segment` column of `unified.instruments` itself.

Everything else about the construction, the required identity fields, the re-raised not-found error and the prefixed segment check follows `src/tradingmachine/assets/equities.py`, and the reasoning is not repeated here. See `.claude/notes/src/tradingmachine/assets/equities.py.md` under "Why the identity arguments are required", "Why the not-found error is re-raised" and "Why the segment check compares the whole prefixed name".

## A bond is named by its ISIN

This is the one place in UBI where an instrument's symbol is an ISIN rather than a ticker, and it is the single most surprising thing about using this module. UBI's `utilities/crossref.py` gives the reason: an ISIN is "the only identity India's one-off corporate bonds and NCDs have that reconciles across brokers, their tickers being too inconsistent to match on". Zerodha and Shoonya carry no ISIN column at all and have one backfilled for them, and a row whose ISIN cannot be resolved is dropped to `uncategorised` rather than identified wrongly.

Measured on 2026-09-20:

| Segment | Rows | ISIN symbols | Other symbols |
|---|---|---|---|
| `nse_fixed_income` | 6,816 | 6,737 | 79 |
| `bse_fixed_income` | 14,614 | 14,614 | 0 |

The 79 exceptions are the interest rate underlyings on the nse, named by a rate code such as `633GS2035` or `577GS2030`. They matter out of proportion to their number, because they are the instruments the futures and options are written on, and they carry no tick size from any broker: UBI nulls both lot and tick for that population deliberately. A sovereign gold bond is in this family too, keyed by its ISIN, rather than with commodities.

So `FixedIncome(exchange="nse", symbol="IN000126C010")` is the ordinary case and `FixedIncome(exchange="nse", symbol="633GS2035")` the unusual one, and `search` is the way to get from a half-remembered ISIN to a whole one.

## What UBI does not have for fixed income

Two gaps are large enough that the module docstring states them, so that a caller does not read a raised error as a bug in this code.

**A cash bond and a rate index have no quote.** Only Stoxkart carries them, and Stoxkart does not serve quotes, so `quote`, `last_price`, `ohlc` and every order-book value raise `ServiceUnavailableError` with "no recent quote is cached, and no broker that serves quotes carries this instrument". Stoxkart's `order_symbol` for the cash bond is also null, so there is no broker to send an order to either. `FixedIncome` is useful today for identity, discovery and holdings, and for nothing else. The three derivative classes are quoted normally, by Fyers, Stoxkart and Zerodha.

**Nothing in this family has candles.** `prices(days=30)` returned `None` for all five resolvable classes, including the derivatives that do have live quotes. UBI's `historical/utilities/unified/sources.py` says why for the derivatives, in as many words: "No derivative bars are stored yet, so this is policy only." So the roughly 192 analysis methods inherited through `Instrument` have nothing to work on here. They are still present, because they come with the base class, and they will start working if UBI's coverage grows.

## Why FixedIncomeIndexOption exists at all

`fixed_income_index_options` is a name in UBI's canonical vocabulary that no broker fills. A grep of UBI returns three hits for it, all in vocabulary tables, and no mapping rule anywhere. It is not merely empty today; nothing in UBI can currently put a row in it.

The user chose on 2026-09-20 to build the class anyway, so that the family is symmetrical with the equity one and with the asset classes still to come, and so that the contracts work the moment UBI gains a rule. The class needs no special case, because the empty segment degrades cleanly and this was checked directly: `/details` answers `NotFoundError`, which the constructor turns into `FixedIncomeIndexOptionError` like any other miss, and `/master` returns zero rows, so `expiries` gives `[]`, `strikes` gives `[]` and `chain` gives `None`. Only a genuinely misspelt segment gives `BadRequestError`. Its docstrings say plainly that it resolves nothing today.

## Holdings

`FixedIncome` carries the same six holdings members as `Equity`, copied rather than shared, and no other class in the module has them: a derivative leaves a position rather than a holding, and an index cannot be held. `fixed_income` is the fifth of the six segments in UBI's `CASH_SEGMENTS`, which is the set a holding resolves against, so a bond is reported exactly as a share is.

Two differences from a share's holding are worth knowing, and the `holdings` docstring states both:

- The row's `symbol` and `isin` hold the same string, because the symbol already is the ISIN. The `symbol` fallback that exists for UBI's cross-exchange merge is therefore matching on an ISIN here, which makes it more reliable than it is for a share rather than less.
- A bond held only at Groww is not reported at all. UBI resolves a Groww holding by the ticker the broker sends rather than by a token, and looks that ticker up among symbols that are ISINs, so it never matches.

The rest follows `equities.py` exactly, including the fixed `cnc` product and the rule that only unpledged units can be sold. The reasoning is in `.claude/notes/src/tradingmachine/assets/equities.py.md` under "Acting on a holding, and what it is worth" and is not repeated.

## A hazard this project cannot fix

UBI's own order routing for fixed income derivatives looks wrong, and it is recorded here because the first person to place such an order will need somewhere to start.

UBI classifies `fixed_income_futures`, `fixed_income_options` and `fixed_income_index_futures` under the `securities` asset class in `utilities/broker_orders/utilities/tradeable_segments.py`, so their market tuple resolves to the equity derivative venue, `NFO` at Zerodha. But the instruments are sourced from the currency-derivative files, `CDS` at Zerodha and `NSECD` elsewhere, and Zerodha's own market table has the correct `CDS` entry sitting unused for this purpose. The same misclassification means quantity is sent in plain units rather than lots, although rate futures are lot-quoted, and that the session window closes at 16:00 although these contracts trade until 17:00.

None of this was verified, because verifying it would mean sending a real order, which is not something to do for a check. It is inference from reading UBI's source on 2026-09-20. Nothing in this module works around it: the fix belongs in UBI.

`fixed_income_indices` is absent from UBI's tradeable segments altogether, which agrees with `FixedIncomeIndex` being built on `NonTradeableInstrument`.

## Verified on 2026-09-20

A live check against UBI on `127.0.0.1:8080`, from a scratchpad script. Five classes resolved and the sixth raised its own error, as intended.

| Class | Contract | Segment resolved | `lot_size` | `tick_size` | Brokers | `last_price` |
|---|---|---|---|---|---|---|
| `FixedIncome` | nse IN000126C010 | `nse_fixed_income` | 1 | 0.01 | stoxkart | no quote |
| `FixedIncome` | nse 633GS2035 | `nse_fixed_income` | 1 | None | stoxkart | no quote |
| `FixedIncome` | bse IN000126C010 | `bse_fixed_income` | 1 | 0.01 | stoxkart | no quote |
| `FixedIncomeFutures` | 633GS2035 2026-09-24 | `nse_fixed_income_futures` | 1 | 0.0025 | fyers, stoxkart, zerodha | 97.81 |
| `FixedIncomeOption` | 633GS2035 2026-09-24 97.25 CE | `nse_fixed_income_options` | None | 0.0025 | stoxkart, zerodha | 1.58 |
| `FixedIncomeIndex` | ONMIBOR | `nse_fixed_income_indices` | 1 | None | stoxkart | no quote |
| `FixedIncomeIndexFutures` | ONMIBOR 2026-09-30 | `nse_fixed_income_index_futures` | 1 | 0.0025 | fyers, stoxkart, zerodha | 5.3 |

Every shape matched the table above. `prices(days=30)` returned `None` for all seven. The rate underlying `633GS2035` has no tick size, as expected, and the option has no agreed lot size either. The tradeable split is right: `FixedIncomeFutures` has the order-book methods and `FixedIncomeIndex` does not, and only `FixedIncome` has `holdings`.

Discovery, live:

| Call | Result |
|---|---|
| `FixedIncome.search(exchange="bse", term="IN0001")` | 6 rows, first `IN000126C010` |
| `FixedIncome.search(exchange="nse", term="GS2035")` | 6 rows: `633GS2035`, `664GS2035`, `667GS2035`, `R633GS2035`, … |
| `FixedIncomeIndex.search(exchange="nse", term="MIBOR")` | 1 row, `ONMIBOR` |
| `FixedIncomeIndex.search(exchange="nse", term="GS")` | 1 row, `10YGS7` |
| `FixedIncomeFutures.expiries(underlying_symbol="633GS2035")` | 2026-09-24, 10-29, 11-26, 12-31, 2027-03-25 |
| `FixedIncomeOption.expiries(underlying_symbol="633GS2035")` | 2026-09-24, 10-29, 11-26, 12-31 |
| `FixedIncomeOption.strikes(expiry_date=2026-09-24)` | 47 strikes, 91.5 upward in steps of 0.25 |
| `FixedIncomeOption.chain(expiry_date=2026-09-24)` | 94 rows, which is the 47 strikes as calls and puts |
| `FixedIncomeIndexFutures.expiries(underlying_symbol="ONMIBOR")` | six dates, 2026-09-30 to 2027-06-30 |
| `FixedIncomeIndexFutures.contracts(exchange="nse")` | 6 rows, the whole segment |
| `FixedIncomeIndexOption.expiries`, `strikes`, `chain` | `[]`, `[]`, `None`, without raising |

The check that matters passed: the row in the middle of the option chain, `633GS2035 2026-09-24 97.25 PE`, was turned into a `FixedIncomeOption` and UBI returned the same `instrument_id`, `f7ad1c24-0ccc-5e61-9fc2-3c3a848d386a`, so discovery and construction agree on what an instrument is.

Every error fired and was catchable as `InstrumentError`, each with the original `InstrumentError` as its `__cause__`:

| Case | Error raised |
|---|---|
| `FixedIncome(exchange="nse", symbol="IN0000000000")` | `FixedIncomeError` |
| `FixedIncome(exchange="nse", symbol="ONMIBOR")`, an index asked for as a bond | `FixedIncomeError` |
| `FixedIncomeIndex(exchange="nse", symbol="IN000126C010")`, a bond asked for as an index | `FixedIncomeIndexError` |
| `FixedIncomeOption` at strike 999999 | `FixedIncomeOptionError` |
| `FixedIncomeIndexFutures` expiring 2001-01-25 | `FixedIncomeIndexFuturesError` |
| `FixedIncomeIndexOption`, anything at all | `FixedIncomeIndexOptionError` |
| `FixedIncomeFutures` with no `expiry_date` | `TypeError`, raised by Python before any request |

## The holdings members, checked on 2026-09-20

The account holds no bond, so `holdings`, `holdings_value` and `holdings_pnl` all returned `None` against the real portfolio, and a scan of the holdings document found zero rows in any fixed income segment. The live check therefore proves the not-held path and nothing more.

The three order methods were exercised offline, with `place_order` replaced by a recorder and `holdings` replaced by a fabricated row, exactly as `Equity`'s were. **No order was sent.**

| Holding | Call | What it did |
|---|---|---|
| not held | `add_to_holdings(2)` | recorded buy 2 as `cnc` |
| not held | `reduce_holdings(5)` | `HoldingError`, nothing is held |
| not held | `liquidate_holdings()` | `HoldingError`, nothing is held |
| 10 held, none pledged | `add_to_holdings(2)` | recorded buy 2 as `cnc` |
| 10 held, none pledged | `reduce_holdings(5)` | recorded sell 5 as `cnc` |
| 10 held, none pledged | `liquidate_holdings()` | recorded sell 10 as `cnc` |
| 10 held, 4 pledged | `reduce_holdings(5)` | recorded sell 5 as `cnc`, since 6 are free |
| 10 held, 4 pledged | `liquidate_holdings()` | recorded sell 6 as `cnc`, leaving the 4 pledged |
| 10 held, all pledged | `reduce_holdings(5)` | `HoldingError` naming all three figures |
| 10 held, all pledged | `liquidate_holdings()` | `HoldingError`, every unit is pledged |

Eight orders were recorded and none was sent. No real order has ever gone through these methods.
