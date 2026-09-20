# Commodities

`assets.commodities` is the same six classes again, on UBI's commodity segments. It is the first
family outside equities where the inherited analysis methods actually return something, and the
first where an order's quantity means something different from a count of units.

| Class | Base | Segment | Named by |
| --- | --- | --- | --- |
| `Commodity` | `TradeableInstrument` | `commodities` | exchange, symbol |
| `CommodityFutures` | `TradeableInstrument` | `commodity_futures` | exchange, underlying symbol, expiry |
| `CommodityOption` | `TradeableInstrument` | `commodity_options` | exchange, underlying symbol, expiry, strike, option type |
| `CommodityIndex` | `NonTradeableInstrument` | `commodity_indices` | exchange, symbol |
| `CommodityIndexFutures` | `TradeableInstrument` | `commodity_index_futures` | exchange, underlying symbol, expiry |
| `CommodityIndexOption` | `TradeableInstrument` | `commodity_index_options` | exchange, underlying symbol, expiry, strike, option type |

UBI carries commodities on `mcx`, `ncdex` and `nse`, and the indices and their derivatives on
`mcx` and `ncdex` only. Symbols are readable tickers such as `GOLD`, `CRUDEOIL` and `ALUMINIUM`
for a commodity and `MCXBULLDEX` or `MCXCOMDEX` for an index, and a derivative's underlying symbol
matches its underlying's symbol exactly, so this family has none of
[fixed income's](fixed-income.md) ISIN awkwardness.

```python
from assets import commodities

expiries = commodities.CommodityFutures.expiries(exchange="mcx", underlying_symbol="GOLD")
contract = commodities.CommodityFutures(
    exchange="mcx",
    underlying_symbol="GOLD",
    expiry_date=expiries[0],
)
price = contract.last_price()
strength = contract.relative_strength_index(window=14, days=90)
```

## Quantity is a whole number of lots

!!! danger "This is the easiest thing in the project to get expensively wrong"

    An equity or bond order is a securities-market order and its quantity is a plain count of
    units. A commodity order is not. UBI measures the quantity against the contract's size and
    refuses anything that is not an exact multiple.

    ```text
    buy_at_market_price(quantity=1)    on MCX GOLD  ->  HTTP 400
                                           quantity must be a whole number of lots of 100
    buy_at_market_price(quantity=100)  on MCX GOLD  ->  one lot
    ```

The figure you pass is in quotation units rather than in lots, and UBI converts it to whatever
each broker counts in before sending, so the same number works whichever broker takes the order.
On the `ncdex` that quotation unit is tonnes, although prices are quoted in quintals.

Nothing in this module checks the multiple locally. That follows the standing rule that quantities
reach UBI exactly as given, and it means the error arrives from UBI as a `BadRequestError` rather
than from here.

## Neither a commodity nor a commodity index can be ordered

`Commodity` is a `TradeableInstrument`, because its segment does not end in `_indices`, so it
inherits `place_order` and all twenty-eight price wrappers. Every one of them will be refused, for
two independent reasons on UBI's side: no broker declares a cash market for the commodity asset
class, so broker selection passes every broker over, and UBI's contract size check refuses any
non-securities order whose shape is not a future or an option.

The rows in the `commodities` segment are the exchange's underlying reference records rather than
tradeable spot contracts. `CommodityIndex` cannot be traded either, by the ordinary rule that an
index is a `NonTradeableInstrument`.

## No holdings, ever

No class here has `holdings` or anything built on it, and that is not a choice made in this
module. UBI's list of cash segments covers equities, exchange-traded funds, investment trusts,
mutual funds, fixed income and its uncategorised catch-all, and nothing else. A holding whose
token names a commodity is filtered out on UBI's side, so a commodity can never be reported as a
holding.

Positions are a different matter and do cover this family, so the position members inherited from
`TradeableInstrument` are meaningful here. See [Positions](../guides/positions.md).

## A 503 here may not mean UBI is down

UBI decides each contract's size once every morning from the exchanges' own fields rather than
from brokers' lot sizes, because the broker majority rule gave wrong answers in this family. When
its sources disagree, the contract cannot be traded that day at all.

```python
from ubi_client import exceptions

try:
    contract.buy_at_market_price(quantity=100, product="nrml")
except exceptions.ServiceUnavailableError as error:
    print(error.detail.get("contract_size_status"))
```

| `contract_size_status` | Meaning |
| --- | --- |
| `conflict` | The exchange fields disagree with each other |
| `undecided` | No decision was reached this morning |
| `no_source` | Nothing supplied a contract size |
| `single_source` | Only one source supplied it, which is the normal state for `bse` currency and `ncdex` commodity contracts |

So a 503 from an order in this family means UBI does not trust the contract's size today, rather
than that UBI is unavailable.

## Quotes and candles

A commodity and a commodity index have no quote, so `quote`, `last_price`, `ohlc` and the
order-book values raise `ServiceUnavailableError` on `Commodity` and `CommodityIndex`. Every
broker's tick normaliser maps the commodity venue codes to the derivative family, so a tick for a
row in those two segments can never resolve. The reason is different from fixed income's, where no
quote-serving broker carries the instrument at all.

The four derivative classes are quoted normally and, unlike anything else outside equities, **they
have candles**. That was measured rather than inferred, and it is what makes this the first family
outside equities where the roughly 190 inherited analysis methods have data to work on.

One more quirk: MCX and NCDEX derivatives are the only instruments in UBI allowed a negative
price, which matters for spread contracts.
