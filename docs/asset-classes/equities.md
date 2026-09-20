# Equities

`tradingmachine.assets.equities` is the family everything else was modelled on. Six classes cover UBI's six
equity segments, and every capability in the project is present here: candles, quotes, the order
book, orders, positions, holdings and discovery.

| Class | Base | Segment | Named by |
| --- | --- | --- | --- |
| `Equity` | `TradeableInstrument` | `equities` | exchange, symbol |
| `EquityFutures` | `TradeableInstrument` | `equity_futures` | exchange, underlying symbol, expiry |
| `EquityOption` | `TradeableInstrument` | `equity_options` | exchange, underlying symbol, expiry, strike, option type |
| `EquityIndex` | `NonTradeableInstrument` | `equity_indices` | exchange, symbol |
| `EquityIndexFutures` | `TradeableInstrument` | `equity_index_futures` | exchange, underlying symbol, expiry |
| `EquityIndexOption` | `TradeableInstrument` | `equity_index_options` | exchange, underlying symbol, expiry, strike, option type |

## Building one

```python
from tradingmachine.assets import equities

share = equities.Equity(exchange="nse", symbol="RELIANCE")

nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")

option = equities.EquityIndexOption(
    exchange="nse",
    underlying_symbol="NIFTY",
    expiry_date="2026-09-29",
    strike_price=25000,
    option_type="CE",
)
```

A derivative is not given an object for its underlying. `option.underlying_symbol` is the string
`"NIFTY"`, and if you want the index itself you build `EquityIndex(exchange="nse", symbol="NIFTY")`
yourself. UBI joins the two only by that string matching, with no key between them, and the match
does not hold for every index.

## Holdings live on `Equity` alone

A share is the only thing in this family that can sit in a demat account. A futures contract or an
option is a position, not a holding, and an index cannot be held at all, so the six holdings
members exist only on `Equity`.

| Member | What it does |
| --- | --- |
| `holdings` | The merged row for this share across every broker, or `None` |
| `holdings_value` | Quantity times last price, or `None` when UBI has no price |
| `holdings_pnl` | `day_change`, `day_change_percentage` and `unrealized` |
| `add_to_holdings(...)` | A `cnc` buy |
| `reduce_holdings(...)` | A `cnc` sell, measured against the free quantity |
| `liquidate_holdings(...)` | A `cnc` sell of the whole free quantity |

The three writing methods always send `cnc`, because delivery is the only product that buys into
or sells out of a demat holding. Selling works on the free quantity, which is the holding minus
anything pledged as collateral, and `HoldingError` covers a share that is not held, a sale larger
than the free quantity, and a holding that is entirely pledged. See
[Holdings](../guides/holdings.md).

!!! note "A holding's profit and loss is not shaped like a position's"

    A holding reports `day_change`, `day_change_percentage` and `unrealized`. A position reports
    `realized`, `unrealized` and `total`. The two dictionaries share only one key, so code that
    walks both has to branch.

## Finding contracts

Each class offers the discovery calls that make sense for it, and each one supplies its own
segment, so there is nothing to pass but the exchange and the underlying.

```python
matches = equities.Equity.search(exchange="nse", term="RELI")

expiries = equities.EquityFutures.expiries(exchange="nse", underlying_symbol="RELIANCE")
contracts = equities.EquityFutures.contracts(exchange="nse", underlying_symbol="RELIANCE")

strikes = equities.EquityOption.strikes(
    exchange="nse",
    underlying_symbol="RELIANCE",
    expiry_date=expiries[0],
)
chain = equities.EquityOption.chain(
    exchange="nse",
    underlying_symbol="RELIANCE",
    expiry_date=expiries[0],
)
```

| Call | On | Returns |
| --- | --- | --- |
| `search` | `Equity`, `EquityIndex` | A `DataFrame` of identities, or `None` |
| `expiries` | the four derivative classes | A list of `datetime.date`, soonest first |
| `contracts` | `EquityFutures`, `EquityIndexFutures` | A `DataFrame` of identities |
| `strikes` | `EquityOption`, `EquityIndexOption` | A list of `float` strikes, lowest first |
| `chain` | `EquityOption`, `EquityIndexOption` | A `DataFrame` of every option for one expiry |

They return identity rows rather than instrument objects on purpose: a 214-contract chain would
otherwise mean 214 lookups. Build the few you actually want from the rows. See
[Finding instruments](../guides/discovery.md).

## What can go wrong

| Exception | When |
| --- | --- |
| `EquityError` and its five siblings | UBI has nothing matching, or the instrument found is outside the class's segment |
| `TradeableInstrumentError` | You reached for an index through a tradeable class |
| `HoldingError` | The share is not held, the sale exceeds the free quantity, or everything is pledged |
| `OrderError` | A price-named wrapper found the order book empty on the side it needed |
