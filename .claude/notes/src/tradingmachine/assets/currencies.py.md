# src/tradingmachine/assets/currencies.py

This module holds the six currency classes: `Currency`, `CurrencyFutures`, `CurrencyOption`, `CurrencyIndex`, `CurrencyIndexFutures` and `CurrencyIndexOption`. They were ported on 2026-09-20 from `src/tradingmachine/assets/currencies.py` in the old tradingmachine project at `/run/media/pramod/6959D90B1DAD7E59/backup_20260910/pramod/Downloads/tradingmachine-master/`. Funds and mutual funds are the last families still to come.

It is a copy of `src/tradingmachine/assets/commodities.py`, which is a copy of the two before it. Nothing was factored out and no existing module was touched.

| Class | Base class | UBI segment | Shape | Instruments in UBI |
|---|---|---|---|---|
| `Currency` | `TradeableInstrument` | `currencies` | security | nse 7, bse 15 |
| `CurrencyFutures` | `Futures` | `currency_futures` | future | nse 261, bse 879 |
| `CurrencyOption` | `Option` | `currency_options` | option | nse 23,527, bse 104,769 |
| `CurrencyIndex` | `NonTradeableInstrument` | `currency_indices` | security | **none** |
| `CurrencyIndexFutures` | `IndexFutures` | `currency_index_futures` | future | **none** |
| `CurrencyIndexOption` | `IndexOption` | `currency_index_options` | option | **none** |

Currencies trade on the `nse` and the `bse` only. UBI carries seven pairs on the nse, `EURINR`, `EURUSD`, `GBPINR`, `GBPUSD`, `JPYINR`, `USDINR` and `USDJPY`, and the bse adds over-the-counter variants such as `USDINROTC` and `USDINROTCD`. Symbols are the readable pair names, and a derivative's `underlying_symbol` matches its underlying's `symbol`.

The construction pattern and its reasoning follow the earlier modules and are recorded in `.claude/notes/src/tradingmachine/assets/equities.py.md`.

## Half the family does not exist

`currency_indices`, `currency_index_futures` and `currency_index_options` are names in UBI's canonical vocabulary that hold no rows on any exchange, and no broker rule maps anything into them. India has no traded currency index for them to fill, so unlike the empty fixed income segment these are unlikely ever to populate.

The user chose on 2026-09-20 to write all six classes anyway, as with fixed income, so that every asset-class module has the same shape and so that the contracts work the moment UBI gains a mapping. This is the largest empty share of any family: three classes of six.

They need no special case, because an empty segment degrades on its own, which was checked. A lookup gets `NotFoundError` from UBI, which the constructor turns into the class's own error like any other miss, and `/master` returns zero rows, so `expiries` and `strikes` give `[]` while `contracts`, `chain` and `search` give `None`. Their docstrings say plainly that they resolve nothing today.

## No holdings members

As with commodities, and for the same reason: UBI's `CASH_SEGMENTS` does not include `currencies`, so a currency can never be reported as a holding, and `bin/unified/holdings` resolves against nothing else. Positions do cover the family, so the inherited position members are meaningful.

## A currency pair cannot be ordered or quoted

`Currency` is built on `TradeableInstrument`, because its segment does not end in `_indices`, so it inherits `place_order`, the thirty-two price wrappers and the order-book methods. None of them can work. Its rows are the exchange's underlying reference records, reached through Kotak's `UNDCUR` and Stoxkart's `UNDCUR` and `CUR` instrument types, rather than tradeable spot contracts; no broker declares a cash market for the currency asset class; and UBI's contract size check refuses any order in this family that is not a future or an option.

Having a method is not the same as the method working. The live check confirms that `Currency` reports `hasattr(pair, "bids")` as True while `last_price` raises `ServiceUnavailableError`, because no broker's tick stream resolves a token to a `currencies` row: every currency venue code maps to the derivative family, and a `currencies` row is not in it.

## The lot size reported is not the lot an order is measured against

This is the sharpest trap in this module and it is worth stating on its own.

An order's quantity is counted in quotation units and must be a whole number of lots, as for commodities, because a currency market is not a securities market. But the `lot_size` attribute on the instrument and the lot UBI measures an order against come from two different places.

`lot_size` comes from `/api/instruments/details`, which takes the plurality of the brokers' own figures. For NSE `USDINR` that gives **1**, because five brokers count in lots against Stoxkart's 1000, and the live check confirms it. UBI's own notes record that this rule "gave NSE USDINR a lot of 1" and that "the brokers disagreed on 99% of live NSE currency options", which is precisely why orders do not use it. Orders read `unified.contract_sizes` instead, decided each morning from the exchanges' own contract-size fields.

So a caller must not compute an order quantity from `lot_size` in this family. The figure to trust is whatever UBI's rejection message names when a quantity is not a whole number of lots. The same caution applies on the bse, where the live check shows `lot_size` 1000 for the same pair from Stoxkart alone, and where a contract trades on that single source.

An order can also be refused with HTTP 503 and a `contract_size_status` of `conflict`, `undecided`, `no_source` or `single_source`, meaning UBI does not trust the contract's size that day rather than that UBI is unavailable. On 2026-09-15 nine GBPINR and JPYINR options were in that state, and 302 NSE currency options carried by Flattrade alone had no contract size at all.

## No candles anywhere, and no quote on the bse

UBI stores no candles for any currency segment, so `prices` returns None throughout and the inherited analysis methods have nothing to work on. That makes currencies the opposite of commodities, whose derivatives do have candles.

Quote coverage also differs by exchange, which the earlier families did not. The nse derivatives are quoted; the bse ones resolve but have no quote at all. Fyers' currency derivatives are deliberately dropped from UBI's tick streams, because its fixed divisor is a hundred times wrong for four-decimal pairs.

## Verified on 2026-09-20

A live check against UBI on `127.0.0.1:8080`, from a scratchpad script. **No order was sent**, and this module has no method that could send one without being asked.

| Class | Contract | Segment | `lot_size` | `tick_size` | Brokers | `last_price` | Candles |
|---|---|---|---|---|---|---|---|
| `Currency` | nse USDINR | `nse_currencies` | 1 | None | 2 | no quote | None |
| `CurrencyFutures` | nse USDINR 2026-09-25 | `nse_currency_futures` | 1 | 0.0025 | 6 | 96.0325 | None |
| `CurrencyOption` | nse USDINR 2026-09-25 95.625 CE | `nse_currency_options` | 1 | 0.0025 | 5 | 1.32 | None |
| `CurrencyFutures` | bse USDINR 2026-09-25 | `bse_currency_futures` | 1000 | 0.0025 | 1 | no quote | None |

The two lot sizes for the same pair on different exchanges, 1 on the nse and 1000 on the bse, are the divergence described above. No class has a `holdings` attribute.

The three empty classes degraded exactly as intended, without raising:

| Call | Result |
|---|---|
| `CurrencyIndex.search(exchange="nse", term="USD")` | `None` |
| `CurrencyIndexFutures.expiries` | `[]` |
| `CurrencyIndexFutures.contracts` | `None` |
| `CurrencyIndexOption.expiries` | `[]` |
| `CurrencyIndexOption.strikes` | `[]` |
| `CurrencyIndexOption.chain` | `None` |

Discovery, live:

| Call | Result |
|---|---|
| `Currency.search(exchange="nse", term="INR")` | 4 rows: `EURINR`, `GBPINR`, `JPYINR`, `USDINR` |
| `Currency.search(exchange="bse", term="USD")` | 9 rows, including the over-the-counter variants `USDINROTC` and `USDINROTCD` |
| `CurrencyFutures.expiries(exchange="nse", underlying_symbol="USDINR")` | weekly, 2026-09-25, 09-28, 10-01, 10-09, … |
| `CurrencyFutures.contracts(exchange="nse")` | 129 rows |
| `CurrencyOption.strikes` and `chain` for 2026-09-25 | 88 strikes over 176 rows |

The check that matters passed: the row in the middle of the chain, `USDINR 2026-09-25 95.625 CE`, rebuilt into a `CurrencyOption` and UBI returned the same `instrument_id`, `8f220507-579b-50e4-a1f4-e6e42807da77`.

Every error fired with the original `InstrumentError` as its `__cause__` and was catchable as `InstrumentError`:

| Case | Error raised |
|---|---|
| an unknown pair symbol | `CurrencyError` |
| a futures contract with no such expiry | `CurrencyFuturesError` |
| an option at an impossible strike | `CurrencyOptionError` |
| a currency index, any symbol | `CurrencyIndexError` |
| an index futures contract, any arguments | `CurrencyIndexFuturesError` |
| an index option, any arguments | `CurrencyIndexOptionError` |
| a futures contract with no `expiry_date` | `TypeError`, before any request |

## The derivative bases, since 2026-09-28

On 2026-09-28 the four derivative classes in this module moved onto the derivative bases in `src/tradingmachine/assets/instruments.py`, at the user's request: `CurrencyFutures` onto `Futures`, `CurrencyOption` onto `Option`, `CurrencyIndexFutures` onto `IndexFutures` and `CurrencyIndexOption` onto `IndexOption`. The full reasoning is in `.claude/notes/src/tradingmachine/assets/instruments.py.md`, under "The derivative bases".

Each class kept its constructor, its error class and its docstrings, and gained one line, `SEGMENT = <the module's segment constant>`. Its own copies of `expiries`, `contracts`, `strikes` and `chain` were deleted, because they were identical in all sixteen derivative classes apart from the segment, and the bases now define each of them once, reading `cls.SEGMENT`. The calls and their signatures are unchanged for a caller. Nothing specific to the family was lost with them: the strike units live in each constructor's `strike_price` description, and the classes on empty segments say so in their class docstrings.

The constructors still wrap `super().__init__` and re-raise `InstrumentError` as the class's own error. That wrap now also covers the bases' shape and segment checks, which could in principle relabel a `FuturesError` as "UBI has no such contract". It cannot happen, because the constructor passes its own segment constant and UBI resolves that segment to exactly one shape, the same argument that already covered the segment check below it.

The derivative members that need the underlying's price, `underlying_price`, `basis`, `basis_percent`, `cost_of_carry`, `intrinsic_value`, `time_value`, `in_the_money`, `moneyness_percent`, `implied_volatility` and `greeks`, raise `ServiceUnavailableError` in this family. A live check on 2026-09-28 found no quote for the underlying of any currency contract, because no broker that serves quotes carries the currency pair itself. The members that need no quote, such as `days_to_expiry`, `expiry_kind`, `next_expiry` and `contract_value`, work normally.

An nse currency option can still be priced by passing the future's last price as `underlying_price`, since the nse derivatives are quoted. A bse contract cannot, because it has no quote of its own.

Later on 2026-09-28 the four derivative constructors gained an optional `underlying` argument, after the identity fields and before `unified_broker_interface`, which they pass to the base class. The user asked for it because the underlying cannot be found reliably by name; the reasoning is in `.claude/notes/src/tradingmachine/assets/instruments.py.md` under "The underlying can be given". For the option classes here, the useful underlying is the future of the option's own month, since the cash instrument has no quote.

On the evening of 2026-09-28 this family's option classes started finding their underlying as the future on the same underlying that expires first on or after the option, priced with Black-76, and its futures classes lost their default underlying, so their `underlying_price` and basis members raise `UnderlyingError` unless one is given. The reasoning and the live figures are in `.claude/notes/src/tradingmachine/assets/instruments.py.md`, under "How a contract finds its underlying".
