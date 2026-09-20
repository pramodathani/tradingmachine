# Orders

!!! danger "Everything on this page places real orders"

    There is no paper trading mode and no simulator. Every call described here goes to a live
    broker account with real money. The closest thing to a rehearsal is
    `place_order(dry_run=True)`, which asks UBI to build the broker's request and hand it back
    without sending it.

Orders live on `TradeableInstrument`, so every class except the indices has them.

## `place_order` is the only thing that sends

Everything else on this page is a wrapper that works out a price and then calls it.

```python
from assets import equities

share = equities.Equity(exchange="nse", symbol="RELIANCE")

placed = share.place_order(
    transaction_type="buy",
    order_type="limit",
    quantity=1,
    product="cnc",
    price=1450.0,
)
```

| Argument | Values | Notes |
| --- | --- | --- |
| `transaction_type` | `buy`, `sell` | Required |
| `order_type` | `market`, `limit`, `sl`, `sl-m` | Required |
| `quantity` | an `int` | In underlying units, not lots |
| `product` | `cnc`, `mis`, `nrml` | Required, so delivery or intraday is always stated |
| `price` | a `float` | Required for `limit` and `sl`, forbidden for `market` and `sl-m` |
| `trigger_price` | a `float` | Required for `sl` and `sl-m` |
| `validity` | `day`, `ioc` | `None` lets UBI use `day` |
| `disclosed_quantity` | an `int` | `None` discloses the whole order |
| `after_market` | a `bool` | Queue the order for the next session |
| `tag` | up to twenty letters and digits | Your own label |
| `dry_run` | a `bool` | Build the request without sending it |

UBI chooses the broker itself, so no broker is named. The vocabulary is passed as plain strings,
with no enums, because UBI validates it and would have to be asked anyway.

!!! warning "Nothing is checked locally"

    The price is not rounded to the tick size and the quantity is not checked against the lot size.
    Both are sent exactly as given, because UBI and the broker behind it hold those rules. A
    quantity that is not a whole number of lots comes back as a `BadRequestError` from UBI, which is
    the only place that knows the right number. See
    [Commodities](../asset-classes/commodities.md#quantity-is-a-whole-number-of-lots).

UBI couples the price fields to the order type and answers HTTP 400 when they do not agree:

| Order type | `price` | `trigger_price` |
| --- | --- | --- |
| `market` | must be absent | absent |
| `limit` | required | absent |
| `sl` | required | required |
| `sl-m` | must be absent | required |

### Reading the answer

```python
{
    "broker": "...",
    "instrument_id": "...",
    "order_id": "...",
    "outcome": "accepted",
    "status_message": "...",
    "broker_response": {...},
    "skipped": [...],
    "timing_ms": 123,
}
```

!!! warning "`accepted` does not mean the order survived"

    It means the broker took it. The exchange can still refuse it afterwards, which is exactly what
    happens to an ordinary order sent while the market is closed. Neither this class nor UBI checks
    market hours. The order's real fate is read from `orders()`, not from this answer, and
    `after_market=True` is how you deliberately queue one for the next session.

## The twenty-eight price wrappers

Each wrapper names where the price comes from instead of making you work it out. They all take the
same five arguments — `quantity`, `product`, `validity`, `after_market` and `tag` — with `product`
required, so delivery or intraday is always a deliberate choice.

| Group | Methods | Price used |
| --- | --- | --- |
| Market | `buy_at_market_price`, `sell_at_market_price` | Whatever the market asks |
| Limit | `buy_at_limit_price`, `sell_at_limit_price` | The `price` you pass |
| Best of book | `buy_at_best_bid_price`, `buy_at_best_offer_price`, `sell_at_best_bid_price`, `sell_at_best_offer_price` | Level 1 of the named side |
| Deeper in the book | `buy_at_second_best_bid_price` through `sell_at_fifth_best_offer_price` | Levels 2 to 5 of the named side, sixteen methods in all |
| Derived | `buy_at_mid_price`, `sell_at_mid_price` | The midpoint of the spread |
| Derived | `buy_at_volume_weighted_average_price`, `sell_at_volume_weighted_average_price` | The day's volume-weighted average |

The naming is literal, and the pairing is what makes it useful. Buying at the best **bid** joins
the queue and saves the spread but only fills when the market comes to you; buying at the best
**offer** crosses the spread and fills now.

```python
share.buy_at_best_bid_price(quantity=1, product="cnc")     # patient
share.buy_at_best_offer_price(quantity=1, product="cnc")   # immediate
```

Every wrapper that reads the order book raises `assets.exceptions.OrderError` when the side it
needs is empty, which is what the book looks like outside market hours.

## Changing and cancelling

```python
share.modify_order(order_id, price=1455.0)
share.cancel_order(order_id)
outcomes = share.cancel_open_orders()
```

`modify_order` takes at least one field to change, and every field left as `None` keeps what the
order already has. UBI finds the order by id in the brokers' order books, so neither method checks
that the order belongs to this instrument.

`cancel_open_orders` cancels each of this instrument's open orders separately, naming the broker
holding each one, and attempts every one even when an earlier one fails. It reports failures in the
frame it returns rather than raising, so one order that can no longer be cancelled does not leave
the rest open.

| Column | What it holds |
| --- | --- |
| `order_id`, `broker` | Which order this row is about |
| `cancelled` | `True` or `False` |
| `error` | `None`, or the failure's class name and message |

## Reading the order book

UBI serves the whole account's order book and has no endpoint for one instrument, so each of these
reads the book and keeps this instrument's own rows.

| Member | Keeps |
| --- | --- |
| `orders(status=None)` | Everything today, or one status |
| `open_orders()` | `PENDING` and `OPEN`, the ones that can still be changed |
| `completed_orders()` | The ones that filled in full |
| `rejected_orders()`, `cancelled_orders()` | As named |
| `trades()` | The fills rather than the orders |

Each returns a `pandas.DataFrame`, or `None` when no row matches.

!!! note "Ask for open orders with `open_orders`, not `orders(status=...)`"

    An order still waiting in the market is reported as `PENDING` by some brokers and `OPEN` by
    others. `open_orders()` covers both; `orders(status="open")` covers only one.

The book is not merged across brokers, so one order placed at one broker appears once, and the same
instrument traded at two brokers gives a row from each.

## Holdings and positions have their own wrappers

`add_to_holdings`, `reduce_position` and the rest are order wrappers too, but they work out the
direction and the product from what you already hold. See [Positions](positions.md) and
[Holdings](holdings.md).
