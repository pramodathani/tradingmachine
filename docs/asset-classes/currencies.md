# Currencies

`assets.currencies` covers UBI's six currency segments, on the `nse` and the `bse`. Ordering works
as it does for [commodities](commodities.md) rather than for shares, and this is the family with
the thinnest coverage of all: half its classes resolve nothing, and nothing in it has candles.

| Class | Base | Segment | Rows in UBI on 2026-09-20 |
| --- | --- | --- | --- |
| `Currency` | `TradeableInstrument` | `currencies` | nse 7, bse 15 |
| `CurrencyFutures` | `TradeableInstrument` | `currency_futures` | nse 261, bse 879 |
| `CurrencyOption` | `TradeableInstrument` | `currency_options` | nse 23,527, bse 104,769 |
| `CurrencyIndex` | `NonTradeableInstrument` | `currency_indices` | **none** |
| `CurrencyIndexFutures` | `TradeableInstrument` | `currency_index_futures` | **none** |
| `CurrencyIndexOption` | `TradeableInstrument` | `currency_index_options` | **none** |

UBI carries seven pairs on the nse: `EURINR`, `EURUSD`, `GBPINR`, `GBPUSD`, `JPYINR`, `USDINR` and
`USDJPY`. The bse adds over-the-counter variants such as `USDINROTC` and `USDINROTCD`. Symbols are
the readable pair names, and a derivative's underlying symbol matches its underlying's symbol.

```python
from assets import currencies

expiries = currencies.CurrencyFutures.expiries(exchange="nse", underlying_symbol="USDINR")
contract = currencies.CurrencyFutures(
    exchange="nse",
    underlying_symbol="USDINR",
    expiry_date=expiries[0],
)
rate = contract.last_price()
```

## Half the family does not exist

The three index segments hold no rows on any exchange, and no broker rule maps anything into them.
India has no traded currency index for them to carry, so unlike the empty fixed income segment
these are unlikely ever to populate. The classes exist so that every asset-class module has the
same shape and so that they work the moment UBI gains a mapping.

They degrade cleanly, with no special case anywhere in the module:

| Call | Result |
| --- | --- |
| The constructor | The class's own error, such as `CurrencyIndexError` |
| `expiries(...)`, `strikes(...)` | `[]` |
| `contracts(...)`, `chain(...)`, `search(...)` | `None` |

## `lot_size` is not the lot an order is measured against

!!! danger "Never compute an order quantity from `lot_size` in this family"

    The two numbers come from different places and they disagree.

    `lot_size` comes from `/api/instruments/details`, which takes the plurality of the brokers' own
    figures. For NSE `USDINR` that gives **1**, because five brokers count in lots against one
    broker's 1000. Orders are measured against UBI's own contract-size decision, made each morning
    from the exchanges' contract-size fields, which is a different number entirely.

    The figure to trust is whatever UBI's rejection message names when a quantity is not a whole
    number of lots. On the `bse` the same pair reports a `lot_size` of 1000, from a single broker.

This is why UBI stopped using the broker majority rule for contract sizes: it gave NSE `USDINR` a
lot of 1, and the brokers disagreed on 99% of live NSE currency options.

As with commodities, an order can also be refused with HTTP 503 and a `contract_size_status` of
`conflict`, `undecided`, `no_source` or `single_source`, meaning UBI does not trust the contract's
size that day rather than that UBI is unavailable.

## A currency pair cannot be ordered or quoted

`Currency` is a `TradeableInstrument`, so it carries `place_order`, the twenty-eight price
wrappers and the order-book methods, and none of them can work. Its rows are the exchange's
underlying reference records rather than tradeable spot contracts, no broker declares a cash market
for currencies, and UBI's contract size check refuses any order in this family that is not a future
or an option.

Having a method is not the same as the method working. `hasattr(pair, "bids")` is `True` while
`pair.last_price()` raises `ServiceUnavailableError`, because every currency venue code maps to the
derivative family in the tick streams and a `currencies` row is not in it.

## No holdings, ever

As with commodities, and for the same reason: `currencies` is not one of UBI's cash segments, so a
currency can never be reported as a holding. Positions do cover the family, so the inherited
position members are meaningful.

## Coverage of prices varies by exchange

This is the first family where that is true.

| | Candles | Quote |
| --- | --- | --- |
| `nse` derivatives | :material-close: none | :material-check: quoted |
| `bse` derivatives | :material-close: none | :material-close: resolve, but no quote at all |
| `Currency`, on either exchange | :material-close: none | :material-close: none |

UBI stores no candles for any currency segment, so `prices()` returns `None` throughout and the
inherited analysis methods have nothing to work on. That makes currencies the exact opposite of
commodities, whose derivatives do have candles. One broker's currency derivatives are deliberately
dropped from UBI's tick streams as well, because its fixed divisor is a hundred times wrong for
four-decimal pairs.
