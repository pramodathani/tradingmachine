# Positions

A position is what you are holding intraday or on margin, as opposed to a
[holding](holdings.md), which sits in the demat account. Position members live on
`TradeableInstrument`, so every class except the indices has them.

## Reading

Both are properties, and each sends a request to UBI every time it is read, because UBI serves the
whole account's positions and has no endpoint for one instrument.

```python
from tradingmachine.assets import equities

share = equities.Equity(exchange="nse", symbol="RELIANCE")

net = share.net_positions
today = share.day_positions
```

| Property | What it holds |
| --- | --- |
| `net_positions` | This instrument's overall positions, carried forward included |
| `day_positions` | Only what was opened today |
| `positions_value` | Signed quantity times last price, added across products |
| `positions_pnl` | A `dict` of `realized`, `unrealized` and `total` |

`positions_value` keeps the sign, so a long position adds and a short one subtracts. A short
position is an obligation to buy back, which is what the negative number says. UBI prices a holding
for you but not a position, so this is worked out here, and it returns `None` when any position has
no last price rather than quietly reporting a total that is missing a part.

!!! note "A position's profit and loss is not shaped like a holding's"

    A position reports `realized`, `unrealized` and `total`. A holding reports `day_change`,
    `day_change_percentage` and `unrealized`. The two dictionaries share only one key.

## Acting on a position

Four methods change a position, and the useful thing about them is that they work out the
direction from the position itself. A long position is reduced by selling and a short one by
buying, so you never pass a side.

| Method | What it does |
| --- | --- |
| `add_to_position(quantity, ...)` | Makes the position bigger in the direction it already points |
| `reduce_position(quantity, ...)` | Makes it smaller, without turning it around |
| `liquidate_position(...)` | Closes one position completely |
| `liquidate_all_positions(...)` | Closes every position in this instrument, under every product |

```python
share.add_to_position(quantity=5)
share.reduce_position(quantity=2)
share.liquidate_position()
outcomes = share.liquidate_all_positions()
```

All of them take `price`, `validity`, `after_market` and `tag`, and leaving `price` as `None`
sends a market order.

`product` is needed only when you hold more than one position in the same instrument, which
happens when the same share is held under both `cnc` and `mis`. With one position, it is read from
the position itself.

`transaction_type` appears only on `add_to_position`, and only matters when you hold nothing yet:
with no position to read a direction from, the method needs to be told which way to open, and it
needs a `product` for the same reason.

### Who works out the direction

`add_to_position` reads the position here and works the direction out itself, because UBI's own
`add_to_position` reference does not read the position.

`reduce_position` and `liquidate_position` hand that work to UBI. Each sends one order carrying a
`quantity_reference`, `reduce_position` or `liquidate_position`, and UBI reads the position at the
moment it sends the order, chooses the side and sizes the order. Two behaviours follow from that.

| Situation | What happens |
| --- | --- |
| `reduce_position` asks for more than is held | UBI closes the whole position. It never sends more than is held, so it never opens a new position the other way round |
| A product is named that is not held | UBI answers HTTP 409, raised as `ConflictError` |
| No product is named | The positions are read here once, to find the only one held |

Both orders are marked as closing a position, so they may use the share of a broker's daily order
cap that UBI keeps for exits. Because they rely on a quantity reference, they need UBI's order
engine and raise `DirectPlacementError` when UBI is placing orders directly. See
[Orders](orders.md).

`tradingmachine.assets.exceptions.PositionError` covers what is still checked here: there is no
position to act on and none was named, several are held and none was named, a product was named
that is not `cnc`, `mis` or `nrml`, or `add_to_position` was given a side that would reduce the
position rather than add to it.

## The product name changes between reading and ordering

This is the module's one genuine trap. UBI names a position's product one way and accepts orders
named another way, and the mapping is not something you have to do yourself — the methods above
translate — but it will confuse you the first time you print a position row.

| UBI reports a position as | An order is sent as | Means |
| --- | --- | --- |
| `delivery` | `cnc` | Bought to keep |
| `intraday` | `mis` | Closed the same day |
| `carry` | `nrml` | Carried forward on margin |

## Three products cannot be closed through UBI

!!! danger "A `margin_trading`, `cover` or `bracket` position is invisible to most of these methods"

    UBI reports positions under these three products, but they come from order kinds its place
    route cannot send, so there is no way to close them through UBI at all. `add_to_position`,
    `reduce_position` and `liquidate_position` drop them and behave as though they were not there.

    `liquidate_all_positions` is the exception: it sees them and **reports them as ignored** rather
    than passing over them in silence. They have to be closed at the broker directly.

The two reading properties are the other exception. `positions_value` and `positions_pnl` count
every position, including these three, because they are still real money.

## What `liquidate_all_positions` returns

It reads the positions once to list them, then closes each one with its own
`liquidate_position` order, and attempts every one even when an earlier one fails, so a single
refusal does not leave the rest open. It closes only this instrument's positions. To cancel every
open order and close every position in the whole account, use `Account.flatten`; see
[Account](account.md). The outcome is a frame with one row per position, or
`None` when the instrument holds no position at all.

| Column | What it holds |
| --- | --- |
| `product` | As UBI reports it, such as `intraday` |
| `order_product` | As the order was sent, such as `mis`, or `None` for the three that cannot be closed |
| `quantity` | The signed position size |
| `closed` | `True` or `False` |
| `order_id` | The order placed, or `None` |
| `error` | `None`, or the failure, or the text `ignored: UBI cannot send a … order, so close this at the broker` |
