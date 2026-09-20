# Fixed income

`tradingmachine.assets.fixed_income` is the same six classes as [equities](equities.md), built the same way and
copied from that module rather than sharing a base with it. Bonds, rate indices, and the futures
and options written on each.

| Class | Base | Segment | Named by |
| --- | --- | --- | --- |
| `FixedIncome` | `TradeableInstrument` | `fixed_income` | exchange, symbol |
| `FixedIncomeFutures` | `TradeableInstrument` | `fixed_income_futures` | exchange, underlying symbol, expiry |
| `FixedIncomeOption` | `TradeableInstrument` | `fixed_income_options` | exchange, underlying symbol, expiry, strike, option type |
| `FixedIncomeIndex` | `NonTradeableInstrument` | `fixed_income_indices` | exchange, symbol |
| `FixedIncomeIndexFutures` | `TradeableInstrument` | `fixed_income_index_futures` | exchange, underlying symbol, expiry |
| `FixedIncomeIndexOption` | `TradeableInstrument` | `fixed_income_index_options` | exchange, underlying symbol, expiry, strike, option type |

The cash segment is spelled `fixed_income`, not pluralised, where the equity one is `equities`.
That irregularity is UBI's, and it is baked into UBI's cash segment list, its Redis keys and the
`segment` column of its instrument table, so it cannot be tidied here.

## A bond is named by its ISIN

This is the single most surprising thing about the module. Everywhere else in the project a symbol
is a ticker; here it is an ISIN.

```python
from tradingmachine.assets import fixed_income

bond = fixed_income.FixedIncome(exchange="nse", symbol="IN000126C010")
```

The reason is that a one-off corporate bond or non-convertible debenture has no ticker that
reconciles across brokers, and the ISIN is the only identity that does. Measured on 2026-09-20,
`nse_fixed_income` held 6,816 rows of which 6,737 were ISINs, and `bse_fixed_income` held 14,614
rows of which every single one was.

The 79 exceptions matter out of proportion to their number. They are the interest rate underlyings
on the nse, named by a rate code such as `633GS2035`, and they are what the futures and options in
this family are written on.

```python
underlying = fixed_income.FixedIncome(exchange="nse", symbol="633GS2035")

contract = fixed_income.FixedIncomeFutures(
    exchange="nse",
    underlying_symbol="633GS2035",
    expiry_date="2026-09-24",
)
```

Sovereign gold bonds live in this family too, keyed by ISIN, rather than with the commodities.

`search` is how you get from a half-remembered ISIN to a whole one, and it is the most useful
thing on `FixedIncome`.

## Two gaps in UBI's coverage

Neither of these is a fault in this module, and both raise rather than returning something
misleading.

!!! warning "A cash bond and a rate index have no quote"

    Only one broker carries them, and that broker does not serve quotes, so `quote`, `last_price`,
    `ohlc` and every order-book value raise `ServiceUnavailableError` for `FixedIncome` and
    `FixedIncomeIndex`. That broker's order symbol for a cash bond is null as well, so there is no
    broker to send an order to either. `FixedIncome` is useful today for identity, discovery and
    holdings, and for nothing else. The three derivative classes are quoted normally.

!!! warning "Nothing in this family has candles"

    `prices()` returns `None` for every one of the six classes, including the derivatives that do
    have live quotes, because UBI stores no derivative bars yet. The roughly 190 analysis methods
    inherited through `Instrument` are all present and all have nothing to work on. They will start
    returning data if UBI's coverage grows.

## `FixedIncomeIndexOption` resolves nothing

`fixed_income_index_options` is a name in UBI's vocabulary that no broker fills, and nothing in
UBI can currently put a row in it. The class is built anyway so that the family is symmetrical
with every other one and so that it works the moment UBI gains a mapping rule.

It degrades cleanly rather than needing a special case:

| Call | Result |
| --- | --- |
| The constructor, with any arguments | `FixedIncomeIndexOptionError` |
| `expiries(...)` | `[]` |
| `strikes(...)` | `[]` |
| `chain(...)` | `None` |

## Holdings

`FixedIncome` carries the same six holdings members `Equity` does, and no other class in the
module has them. `fixed_income` is one of UBI's cash segments, so a bond is reported in the
account's holdings exactly as a share is. Two differences are worth knowing:

- The holding row's `symbol` and `isin` hold the same string, because the symbol already is the
  ISIN. The symbol fallback that UBI's cross-exchange merge relies on is therefore matching on an
  ISIN here, which makes it more reliable rather than less.
- A bond held only at Groww is not reported at all, because UBI resolves a Groww holding by the
  ticker the broker sends and then looks that ticker up among symbols that are ISINs, which never
  matches.

## A hazard this project cannot fix

!!! danger "UBI's order routing for bond derivatives looks wrong"

    UBI classifies `fixed_income_futures`, `fixed_income_options` and `fixed_income_index_futures`
    under its `securities` asset class, so their market tuple resolves to the **equity** derivative
    venue rather than the currency one, although the instruments are sourced from the
    currency-derivative files. The same misclassification means the quantity is sent in plain units
    although rate futures are lot-quoted, and that the session window closes at 16:00 although
    these contracts trade until 17:00.

    This is inference from reading UBI's source on 2026-09-20, not a verified observation, because
    verifying it would mean sending a real order. Nothing in this module works around it; the fix
    belongs in UBI. The full reasoning is in `.claude/notes/src/tradingmachine/assets/fixed_income.py.md`.
