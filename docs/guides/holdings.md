# Holdings

A holding is what sits in the demat account for the long term, as opposed to a
[position](positions.md), which is intraday or on margin. Unlike positions, holdings are not on
`TradeableInstrument`: they appear only on the classes UBI can actually report a holding for.

| Class | Module |
| --- | --- |
| `Equity` | `tradingmachine.assets.equities` |
| `FixedIncome` | `tradingmachine.assets.fixed_income` |
| `ExchangeTradedFund` | `tradingmachine.assets.funds` |
| `InvestmentTrust` | `tradingmachine.assets.funds` |
| `MutualFund` | `tradingmachine.assets.mutual_funds` |

Nothing in [commodities](../asset-classes/commodities.md) or
[currencies](../asset-classes/currencies.md) has them, because those segments are not in UBI's
cash segment list and a holding whose token names a commodity is filtered out on UBI's side. A
derivative leaves a position rather than a holding, and an index cannot be held at all.

The six members are identical on all five classes, copied into each rather than shared, which is
the project's standing choice about duplication between families.

## Reading

```python
from tradingmachine.assets import equities

share = equities.Equity(exchange="nse", symbol="RELIANCE")

row = share.holdings
value = share.holdings_value
profit = share.holdings_pnl
```

Each of the three is a property, and each sends a request to UBI every time it is read, because
UBI serves the whole account's holdings and has no endpoint for one instrument. All three return
`None` when the instrument is not held.

| Field in `holdings` | What it is |
| --- | --- |
| `instrument_id`, `isin`, `symbol`, `exchange`, `segment` | Identity |
| `quantity` | Units held |
| `collateral_quantity` | Units pledged, which cannot be sold |
| `average_price`, `invested_value` | What was paid |
| `last_price`, `current_value` | What it is worth now |
| `pnl` | A `dict` of `day_change`, `day_change_percentage` and `unrealized` |

`holdings_value` reads UBI's own `current_value` rather than working it out, which is the opposite
of `positions_value`. It counts every unit held, including anything pledged, because a pledged
share is still owned.

!!! note "A holding's profit and loss has no realised figure"

    A holding reports `day_change`, `day_change_percentage` and `unrealized`; a position reports
    `realized`, `unrealized` and `total`. Only `unrealized` means the same thing in both. There is
    no realised figure for a holding, because selling removes units from the holding rather than
    booking a profit against it.

## Acting on a holding

```python
share.add_to_holdings(quantity=10, price=1450.0)
share.reduce_holdings(quantity=4, price=1460.0)
share.liquidate_holdings(price=1460.0)
```

| Method | What it sends |
| --- | --- |
| `add_to_holdings(quantity, ...)` | A `cnc` buy |
| `reduce_holdings(quantity, ...)` | A `cnc` sell, measured against the free quantity |
| `liquidate_holdings(...)` | A `cnc` sell of the whole free quantity |

All three take `price`, `validity`, `after_market` and `tag`. Leaving `price` as `None` sends a
market order, which is fine for a share and wrong for a
[mutual fund](../asset-classes/mutual-funds.md), which has no quote for a market order to be
priced against.

The product is always `cnc` and cannot be changed, because delivery is the only product that buys
into or sells out of a demat holding.

## Selling works on the free quantity

Units pledged as collateral cannot be sold until the broker releases them, so a sale is measured
against what is free rather than against the whole holding.

```text
free quantity = quantity - collateral_quantity
```

`liquidate_holdings` therefore empties the holding only when nothing is pledged; otherwise it
sells what it can and leaves the pledged units alone.

`tradingmachine.assets.exceptions.HoldingError` covers the three ways this fails, and each message names the
figures involved.

| Situation | Message names |
| --- | --- |
| The instrument is not held at all | That there is nothing to sell |
| The sale is larger than the free quantity | The free quantity, the whole holding and the pledged part |
| Every unit is pledged | The whole holding, and that none can be sold |
