# Mutual funds

`tradingmachine.assets.mutual_funds` holds one class, `MutualFund`, on UBI's `mutual_funds` segment. It is the
only instrument in the project that is held rather than traded, and it is kept apart from
[`tradingmachine.assets.funds`](funds.md) for exactly that reason.

| Class | Base | Segment | Rows in UBI on 2026-09-20 |
| --- | --- | --- | --- |
| `MutualFund` | `TradeableInstrument` | `mutual_funds` | 279, on the `nse` only |

A scheme is named by the exchange's code for it, such as `ABSLFTTIDG`, rather than by its
published name, so `search` is usually how you find one.

```python
from tradingmachine.assets import mutual_funds

fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
row = fund.holdings
value = fund.holdings_value

matches = mutual_funds.MutualFund.search(exchange="nse", term="ABSL")
```

## What does not work here

A mutual fund is subscribed to and redeemed at the day's net asset value rather than bought and
sold in a continuous market, and UBI has no quote for one. Only one broker carries the segment,
and it is not a broker that serves quotes.

| Member | Result |
| --- | --- |
| `quote()`, `last_price()`, `ohlc()` | `ServiceUnavailableError` |
| `bids()`, `asks()`, `best_bid()`, and every other order-book value | `ServiceUnavailableError` |
| `prices()` | `None`, because UBI stores no candles |
| The roughly 190 analysis methods | Nothing to work on |

That leaves holding as the thing a `MutualFund` is actually for.

## The full holdings surface, deliberately

`mutual_funds` is one of UBI's cash segments, so a scheme is reported in the account's holdings
exactly as a share is, and `MutualFund` carries the same six holdings members `Equity` does:
`holdings`, `holdings_value`, `holdings_pnl`, `add_to_holdings`, `reduce_holdings` and
`liquidate_holdings`.

The old project gave `MutualFund` holdings **reading** only, on the reasoning that net-asset-value
subscription and redemption do not map onto market and limit orders. The full surface was chosen
here instead, so that no class in this family is an exception a caller has to remember the shape
of. Two things follow from that choice.

The three writing methods send ordinary `cnc` orders, which is the product UBI accepts for this
segment. Whether a broker treats such an order as a subscription is the broker's business, and no
live order has been sent through these methods to find out.

!!! warning "Give these methods a limit price"

    With no quote there is nothing for a market order to be priced against, so a limit price is the
    only sensible form.

    ```python
    fund.add_to_holdings(quantity=10, price=25.0)
    ```

    Leaving the price out still sends a market order rather than refusing, because this project
    does not second-guess what UBI will accept. Nothing here will stop you.
