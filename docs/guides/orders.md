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
from tradingmachine.assets import equities

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
| `quantity` | an `int` | In underlying units, not lots. `None` only when a `quantity_reference` supplies it |
| `product` | `cnc`, `mis`, `nrml` | Required, so delivery or intraday is always stated |
| `price` | a `float` | Required for `limit` and `sl`, forbidden for `market` and `sl-m`, unless a `price_reference` supplies it |
| `trigger_price` | a `float` | Required for `sl` and `sl-m` |
| `validity` | `day`, `ioc` | `None` lets UBI use `day` |
| `disclosed_quantity` | an `int` | `None` discloses the whole order |
| `after_market` | a `bool` | Queue the order for the next session |
| `tag` | up to twenty letters and digits | Your own label |
| `dry_run` | a `bool` | Build the request without sending it |
| `price_reference` | a `dict` | Describe the price rather than state it, such as the second best offer. Engine mode only |
| `quantity_reference` | a `dict` | Describe the quantity rather than state it, such as the whole position. Engine mode only |
| `synthetic` | a `dict` | Make the order one of UBI's synthetic order types. Engine mode only; see [Synthetic orders](synthetic-orders.md) |

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

### Describing the price or the quantity instead of stating it

UBI's order engine can work a price out from the live order book, or a quantity out from the
positions, at the moment it sends the order. You describe what you want, and UBI resolves it.

```python
share.place_order(
    transaction_type="buy",
    order_type="limit",
    quantity=1,
    product="cnc",
    price_reference={"kind": "offer_level", "level": 2},
)
```

| `price_reference` kind | Price used |
| --- | --- |
| `bid_level`, `offer_level` | That level of the named side, with `level` from 1 to 5 |
| `mid` | Halfway between the best bid and the best offer |
| `vwap` | The day's volume-weighted average price |
| `last` | The last traded price |
| `marketable` | The best price on the other side, which is what it takes to fill now |
| `absolute` | The `price` inside the reference, rounded to the tick |

Every price UBI works out is rounded to the tick, towards the passive side except for
`marketable`. Three optional fields nudge it: `buffer_percent`, `offset_percent` and
`offset_ticks`, each of which moves the price towards filling, up for a buy and down for a sell.

| `quantity_reference` kind | Quantity used |
| --- | --- |
| `reduce_position` | Up to `quantity`, but never more than is held, and UBI chooses the side |
| `liquidate_position` | The whole net position, and UBI chooses the side |
| `add_to_position` | Exactly the `quantity` given; it does not read the position |

A `quantity_reference` may name a `product` the positions' way, `delivery`, `intraday` or `carry`.
Asking to reduce or close a position that is not held raises `ConflictError`.

!!! danger "These only work when UBI runs its order engine"

    In direct mode, UBI checks the shape of a `price_reference`, a `quantity_reference` or a
    `synthetic` object and then ignores it. A limit order carrying only a price reference would go
    out at price 0, and a bracket would go out as an unprotected entry. So before the first such
    order, `place_order` sends the same body once as a dry run. Only an answer carrying an
    `intent_id`, which the engine adds to everything it answers, lets the order go ahead;
    otherwise it raises `DirectPlacementError` and nothing is sent. The finding is kept as
    `placement_mode` on the shared client, so this costs one dry run per session.

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

In engine mode the answer also carries an `intent_id`, and a `parent_id` for an order the engine
recorded. A synthetic order that waits for a price or a time comes back with HTTP 202, an `outcome`
of `armed` or `scheduled`, and a `broker` and `order_id` of `None`, because nothing has reached a
broker yet. Keep its `parent_id`.

!!! warning "`accepted` does not mean the order survived"

    It means the broker took it. The exchange can still refuse it afterwards, which is exactly what
    happens to an ordinary order sent while the market is closed. Neither this class nor UBI checks
    market hours. The order's real fate is read from `orders`, not from this answer, and
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

Every wrapper that reads the order book raises `tradingmachine.assets.exceptions.OrderError` when the side it
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

| Property | Keeps |
| --- | --- |
| `orders` | Every order today, whatever its status |
| `open_orders` | `PENDING` and `OPEN`, the ones that can still be changed |
| `completed_orders` | The ones that filled in full |
| `rejected_orders`, `cancelled_orders` | As named |
| `trades` | The fills rather than the orders |

Each gives a `pandas.DataFrame`, or `None` when no row matches. All five are properties, so
reading one sends a request to UBI every time.

!!! note "Ask for open orders with `open_orders`, not by filtering on `OPEN`"

    An order still waiting in the market is reported as `PENDING` by some brokers and `OPEN` by
    others. `open_orders` covers both, while filtering `orders` on `OPEN` alone covers only one. A
    status with no property of its own, such as `EXPIRED`, is found by filtering the `status`
    column of `orders` yourself.

The book is not merged across brokers, so one order placed at one broker appears once, and the same
instrument traded at two brokers gives a row from each.

## Holdings and positions have their own wrappers

`add_to_holdings`, `reduce_position` and the rest are order wrappers too, but they work out the
direction and the product from what you already hold. See [Positions](positions.md) and
[Holdings](holdings.md).
