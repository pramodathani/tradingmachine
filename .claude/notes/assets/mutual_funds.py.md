# assets/mutual_funds.py

This module holds `MutualFund`, the last class ported from the old tradingmachine project at `/run/media/pramod/6959D90B1DAD7E59/backup_20260910/pramod/Downloads/tradingmachine-master/`, on 2026-09-20. With it, every asset class that project had is ported.

| Class | Base class | UBI segment | Shape | Instruments in UBI |
|---|---|---|---|---|
| `MutualFund` | `TradeableInstrument` | `mutual_funds` | security | 279, on the `nse` only |

It is one class, because UBI has no futures or options segment for a mutual fund and carries the segment on one exchange. A scheme is named by exchange and symbol, and the symbol is the exchange's code for the scheme, such as `ABSLFTTIDG`, rather than its published name.

## Why it is its own module

The user chose on 2026-09-20 to keep it apart from `assets/funds.py`, following the old project's split. An exchange traded fund and an investment trust are bought and sold in a continuous market exactly as a share is. A mutual fund is subscribed to and redeemed at the day's net asset value, has no quote at all, and is carried by a single broker. Putting it beside the two exchange-traded classes would suggest it behaves like them.

## What does not work, and why

A mutual fund has no quote. Only Stoxkart carries the segment, and no broker that serves quotes does, so `quote`, `last_price`, `ohlc` and every order-book value raise `ServiceUnavailableError`. UBI stores no candles either, so `prices` returns None and the roughly 192 inherited analysis methods have nothing to work on. The constructor docstring says all of this, so a caller does not read the error as a fault in this module.

That leaves holding as the thing a `MutualFund` is actually for.

## The full holdings surface, deliberately

`mutual_funds` is one of UBI's `CASH_SEGMENTS`, so a scheme is reported in the account's holdings exactly as a share is, and `MutualFund` carries the same six holdings members `assets.equities.Equity` does, copied into the class rather than shared.

The old project gave `MutualFund` holdings **reading** only, on the reasoning that net-asset-value subscription and redemption do not map onto market and limit orders, and that was offered here as the alternative. The user chose the full surface on 2026-09-20, so that no class in this family is an exception a caller has to remember which way round it works.

Two things follow that are worth stating rather than discovering:

The three order methods send ordinary `cnc` orders, which is the product UBI accepts for this segment. Whether a broker treats such an order as a subscription is the broker's business, and no live order has been sent through these methods to find out.

A price should be given. With no quote there is nothing for a market order to be priced against, so a limit price is the only sensible form, and `add_to_holdings(quantity=10, price=25.0)` is the shape to use. Passing None still sends a market order rather than refusing, because this project does not second-guess what UBI will accept; the docstring asks for a price instead.

## Verified on 2026-09-20

A live check against UBI on `127.0.0.1:8080`. **No order was sent.**

```
MutualFund(exchange='nse', segment='nse_mutual_funds', symbol='ABSLFTTIDG')
  segment    nse_mutual_funds   shape security   lot 1   tick 0.01
  brokers    ['stoxkart']
  last_price ServiceUnavailableError
  candles    None
  holdings   None
```

All six holdings members are present. `search(exchange="nse", term="ABSL")` returned 18 rows beginning `ABSLFTTIDG`, `ABSLFTTIDN`, `ABSLFTTIRG`, `ABSLFTTIRN`, `ABSLFTTJDG`, which is the case for searching by the fund house's prefix rather than by words from a scheme's title.

No scheme is held in the account, so the live holdings path proves only the not-held case. The three order methods were exercised offline with `place_order` replaced by a recorder and `holdings` replaced by a fabricated row, over the same four states the earlier modules used, each with an explicit limit price:

| Holding | Call | What it did |
|---|---|---|
| not held | `add_to_holdings(2, price=25)` | recorded buy 2 as `cnc` limit |
| not held | `reduce_holdings(5)`, `liquidate_holdings()` | `HoldingError`, nothing is held |
| 10 held, none pledged | `reduce_holdings(5, price=25)` | recorded sell 5 as `cnc` limit |
| 10 held, none pledged | `liquidate_holdings(price=25)` | recorded sell 10 as `cnc` limit |
| 10 held, 4 pledged | `reduce_holdings(5, price=25)` | recorded sell 5 as `cnc` limit, since 6 are free |
| 10 held, 4 pledged | `liquidate_holdings(price=25)` | recorded sell 6 as `cnc` limit, leaving the 4 pledged |
| 10 held, all pledged | `reduce_holdings(5)`, `liquidate_holdings()` | `HoldingError` naming the pledged units |

Eight orders were recorded and none was sent. No real order has ever gone through these methods.

The errors fired as they do everywhere else, each with the original `InstrumentError` as its `__cause__`:

| Case | Error raised |
|---|---|
| an unknown scheme symbol | `MutualFundError` |
| a share asked for as a scheme | `MutualFundError` |
| a scheme with no `symbol` argument | `TypeError`, before any request |
