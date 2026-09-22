# src/tradingmachine/assets/funds.py

This module holds `ExchangeTradedFund` and `InvestmentTrust`. They were ported on 2026-09-20 from `src/tradingmachine/assets/funds.py` in the old tradingmachine project at `/run/media/pramod/6959D90B1DAD7E59/backup_20260910/pramod/Downloads/tradingmachine-master/`. `MutualFund` is the third of the old project's fund classes and lives in `src/tradingmachine/assets/mutual_funds.py`, kept apart for the reason below.

| Class | Base class | UBI segment | Shape | Instruments in UBI |
|---|---|---|---|---|
| `ExchangeTradedFund` | `TradeableInstrument` | `exchange_traded_funds` | security | nse 353, bse 273 |
| `InvestmentTrust` | `TradeableInstrument` | `investment_trusts` | security | nse 27, bse 27 |

## Two classes rather than six

Every asset-class module before this one has six classes, because UBI carries futures and options on the underlying. It carries none on a fund or a trust: there is no `exchange_traded_fund_futures` segment and no `investment_trust_options` segment in its canonical vocabulary at all, unlike the currency index segments, which exist and are merely empty.

So this family is genuinely two classes, both named by exchange and symbol alone, and there is nothing to leave out and nothing to write speculatively. Both are `security` shape and their identity is a single `symbol` field.

## Why these two are together and the mutual fund is not

The user chose this split on 2026-09-20, following the old project. A fund and a trust are bought and sold on the exchange exactly as a share is: they are quoted continuously, they take ordinary market and limit orders, and their quantity is a plain count of units rather than the whole number of lots a commodity or currency order needs. A mutual fund is subscribed to at the day's net asset value, has no quote at all, and is carried by a single broker, so it sits in its own module.

## The holdings members, and the one behavioural difference

Both classes carry the same six holdings members `tradingmachine.assets.equities.Equity` does, copied into each rather than shared, which is the standing decision for this family of modules. `exchange_traded_funds` and `investment_trusts` are both in UBI's `CASH_SEGMENTS`, so a holding in either resolves exactly as a share's does, and `cnc` is the right product for both.

The one real difference between the two classes is what UBI stores rather than anything in this module. `exchange_traded_funds` is in UBI's `ADJUSTABLE_SEGMENTS` along with equities and investment trusts, and a fund's candles come back adjusted for splits and bonuses with a `price_factor` column. A trust's candles are not stored at all yet, so `prices` returns None for an `InvestmentTrust` and the inherited analysis methods have nothing to work on, even though the trust is quoted and traded normally. The `InvestmentTrust` constructor docstring says so.

Everything else about construction, the required identity fields, the re-raised not-found error and the prefixed segment check follows the earlier modules, and the reasoning is in `.claude/notes/src/tradingmachine/assets/equities.py.md`.

## Verified on 2026-09-20

A live check against UBI on `127.0.0.1:8080`, from a scratchpad script. **No order was sent**; the three order methods were exercised against a recorder with a fabricated holdings row, as `Equity`'s were.

| Class | Instrument | Segment | `lot_size` | `tick_size` | Brokers | `last_price` | Candles |
|---|---|---|---|---|---|---|---|
| `ExchangeTradedFund` | nse NIFTYBEES | `nse_exchange_traded_funds` | 1 | 0.01 | 10 | 266.53 | 42, with `price_factor` |
| `ExchangeTradedFund` | bse NIFTYBEES | `bse_exchange_traded_funds` | 1 | 0.01 | 10 | 266.6 | 41, with `price_factor` |
| `InvestmentTrust` | nse EMBASSY | `nse_investment_trusts` | 1 | 0.01 | 9 | 441.07 | None |

The same fund is listed and quoted on both exchanges at slightly different prices, 266.53 and 266.6, which is the ordinary cross-listing difference rather than anything to correct.

The candle difference is visible in the analysis methods, which is the clearest way to see it. `relative_strength_index(window=14, days=90)` on the fund returned 63 rows:

```
                 datetime  close    rsi_14
2026-09-17 00:00:00+05:30 266.08 29.018966
2026-09-18 00:00:00+05:30 266.53 31.299985
```

The same call on the trust returned None, because UBI stores no candles for that segment.

Discovery, live:

| Call | Result |
|---|---|
| `ExchangeTradedFund.search(exchange="nse", term="NIFTYBEE")` | 1 row, `NIFTYBEES` |
| `ExchangeTradedFund.search(exchange="nse", term="GOLD")` | 26 rows: `GOLD1`, `GOLD360`, `GOLDADD`, `GOLDAXIS`, `GOLDBEES`, `GOLDBETA`, … |
| `InvestmentTrust.search(exchange="nse", term="EMBAS")` | 1 row, `EMBASSY` |
| `InvestmentTrust.search(exchange="nse", term="INVIT")` | 9 rows: `CAPINVIT`, `CUBEINVIT`, `INDUSINVIT`, `IRBINVIT`, `NDRINVIT`, `PGINVIT`, … |

Neither instrument is held in the account, so `holdings` returned None for both and the live holdings path proves only the not-held case. The three order methods were then exercised offline against a recorder, for both classes, over the same four holding states `Equity`'s were:

| Holding | Call | What it did |
|---|---|---|
| not held | `add_to_holdings(2)` | recorded buy 2 as `cnc` |
| not held | `reduce_holdings(5)`, `liquidate_holdings()` | `HoldingError`, nothing is held |
| 10 held, none pledged | `reduce_holdings(5)` | recorded sell 5 as `cnc` |
| 10 held, none pledged | `liquidate_holdings()` | recorded sell 10 as `cnc` |
| 10 held, 4 pledged | `reduce_holdings(5)` | recorded sell 5 as `cnc`, since 6 are free |
| 10 held, 4 pledged | `liquidate_holdings()` | recorded sell 6 as `cnc`, leaving the 4 pledged |
| 10 held, all pledged | `reduce_holdings(5)`, `liquidate_holdings()` | `HoldingError` naming the pledged units |

Sixteen orders were recorded across the two classes and none was sent. No real order has ever gone through these methods.

Every error fired with the original `InstrumentError` as its `__cause__` and was catchable as `InstrumentError`:

| Case | Error raised |
|---|---|
| an unknown fund symbol | `ExchangeTradedFundError` |
| a share asked for as a fund | `ExchangeTradedFundError` |
| an unknown trust symbol | `InvestmentTrustError` |
| a fund asked for as a trust | `InvestmentTrustError` |
| a fund with no `symbol` argument | `TypeError`, before any request |
