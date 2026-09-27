# Order engine

UBI places every order through its order engine, a separate long-running UBI process that sends orders to the brokers and can keep working an order after your request has been answered. This page explains what that means for this library: what the library sends as a description for the engine to work out, why a plain limit order comes back without an order id, what a parent is, and how to read an answer that arrived late.

## Every order goes through the engine

Until 2026-09-27 UBI had a second placement mode, called direct, in which the API worker sent a plain order to the broker itself and quietly ignored anything only the engine understood. UBI removed it that day, so there is now one path for every order, and the library no longer checks which mode UBI is in. The table below shows what the engine does for each part of an order this library can send.

| What the order carries | What the engine does with it |
|---|---|
| A plain order: side, type, quantity, price | Sends it to a broker, as the `simple` type, or holds it first if it is a plain `day` limit order (see [below](#plain-limit-orders-are-held)) |
| `price_reference` | Works the price out from the live quote and rounds it to the tick |
| `quantity_reference` | Works the quantity out from the positions, and chooses the side that closes |
| `synthetic` | Runs the order as one of 53 synthetic order types |
| Every answer | Adds an `intent_id`, and a `parent_id` for an order it recorded |

When the engine is not running, UBI refuses the order before queueing anything, and the library raises `ServiceUnavailableError` with UBI's message `the order engine is not running, so the order was not placed; start unified-orders@order_engine.service`.

## What the library sends as a description

The user decided on 2026-09-26 that order types are built in UBI rather than here. So wherever UBI can work a value out itself, the library sends a small dictionary describing the value instead of computing it. `place_order` accepts three such objects as its last three arguments, and the table below lists them and the members that send each one.

| Object | Describes | Example | Sent by |
|---|---|---|---|
| `price_reference` | Where the price comes from | `{"kind": "offer_level", "level": 1}` | 28 of the 32 price wrappers, such as `buy_at_best_offer_price` and `sell_at_mid_price` |
| `quantity_reference` | How big the order is, from the position held | `{"kind": "liquidate_position", "product": "intraday"}` | `reduce_position`, `liquidate_position` and so `liquidate_all_positions` |
| `synthetic` | Which synthetic order type works the order, with its settings | `{"type": "bracket", "stop_price": 990, "stop_limit_price": 988, "target_price": 1010}` | Every class in `tradingmachine.orders`; the two position methods above, which send `{"type": "simple", "closes_position": true}`; and the two limit wrappers with `hold=False`, which send `{"type": "simple"}` |

UBI documents how each reference becomes a number on [Price and quantity references](https://pramodathani.github.io/unified_broker_interface/rest-api/price-quantity-references/).

### A dry run, captured

The example below is a dry run of a limit buy of one RELIANCE share, priced at the best offer by a `price_reference`, captured from a local UBI on Saturday 2026-09-26, the day before UBI removed direct placement. The answer shows the request UBI would have sent to Stoxkart, the broker it chose, with the price 1226.0 worked out from the best offer, and the `intent_id` the engine adds to every answer. It contains no account identifier.

=== "Python"

    ```python
    from tradingmachine.assets import equities

    reliance = equities.Equity("nse", "RELIANCE")
    answer = reliance.place_order(
        "buy",
        "limit",
        1,
        "cnc",
        price_reference={"kind": "offer_level", "level": 1},
        dry_run=True,
    )
    print(repr(answer))
    ```

=== "Output"

    ```text
    {'broker': 'stoxkart', 'dry_run': True, 'instrument_id': '3f92570a-9924-5bf5-9f9d-e006cd9f4202', 'intent_id': '584e0a7f6cb84dc18fe0e64da9f4db69', 'request': {'json': {'action': 'BUY', 'algo_id': '99999', 'disclose_quantity': '0', 'exchange': 'NSE', 'order_type': 'LIMIT', 'price': '1226.0', 'product_type': 'DELIVERY', 'quantity': '1', 'stop_loss_price': '0', 'token': '2885', 'trailing_stop_loss': '0', 'trigger_price': '0', 'validity': 'DAY'}, 'method': 'POST', 'url': 'https://openapi.stoxkart.com/orders/normal'}, 'skipped': [], 'tag': None, 'timing_ms': {'preparation': 1.98}}
    ```

## Plain limit orders are held

Since 2026-09-27 the engine does not send a plain limit order to a broker straight away. It holds it in its own order book, as a `virtual_limit` order, and sends it only once the other side of the book reaches its price: for a buy, when the best offer is at or below it. A limit that never fills therefore costs no order messages at all, where a resting one costs a place and a cancel. The animation below follows one held buy.

<figure class="diagram">
--8<-- "docs/assets/diagrams/held-limit-order.svg"
<figcaption>Orange dots are the order, green dots are the immediate answer with its parent_id, and blue dots are live quotes; the order reaches a broker only after a quote shows the offer at its price.</figcaption>
</figure>

UBI decides which orders are held by the rule in the table below.

| Order | Held? |
|---|---|
| `limit` with a `price`, `day` validity and no `synthetic` object | Yes |
| `limit` with `after_market=True` | No, sent at once, because the broker queues it for the next session |
| `limit` with `synthetic={"type": "simple"}`, which `hold=False` sends | No, sent at once |
| `limit` with `ioc` validity | No, sent at once |
| `market`, `sl`, `sl-m`, or a `limit` priced only by a `price_reference` | No, sent at once |
| Any order naming another `synthetic` type | Run as that type |

A held order changes what your program sees, in the four ways listed below.

- `place_order` answers with HTTP 202, an `outcome` of `armed`, a `parent_id` and an `order_id` of None, because no broker order exists yet.
- The order is not in `orders` or `open_orders`, which read the brokers' order books. It is in `parents`.
- It is changed by naming its parent: `modify_order(parent_id=..., price=..., quantity=...)`. Only the price and the quantity can change, and nothing is sent to a broker.
- It is cancelled with `cancel_parent(parent_id)`, not `cancel_order`, which needs a broker order id.

### When to send a limit order at once

A held order is sent only when a live quote shows the other side reaching its price, and the engine never acts on a stale quote. An instrument that no broker quotes would therefore wait all day and never be sent. `buy_at_limit_price` and `sell_at_limit_price` take `hold=False` for that case, and the table below lists the members that always pass it.

| Member | Why it sends at once |
|---|---|
| `MutualFund.add_to_holdings`, `reduce_holdings`, `liquidate_holdings` with a price | No broker that serves quotes carries the mutual fund segment |
| `FixedIncome.add_to_holdings`, `reduce_holdings`, `liquidate_holdings` with a price | No broker that serves quotes carries a cash bond |

For any other order, pass `hold=False` to a limit wrapper, or `synthetic={"type": "simple"}` to `place_order`, whenever the order must rest at the exchange straight away.

An after-market limit order needs no `hold=False`. UBI has sent every after-market order to the broker at once since 2026-09-27, because the broker queues it for the next session and no live quote would arrive to release a held one. A live test that evening placed after-market limit orders through `buy_at_limit_price`, `sell_at_limit_price`, `add_to_holdings` and `reduce_holdings`, and every one reached a broker rather than being held.

## Parents

A parent is one order the engine was asked for, such as a bracket, a trailing stop or a held limit order, and its legs are the broker orders it placed. Every order the engine records answers with a `parent_id`, and since 2026-09-27 every row of the order and trade books names its parent in `engine_parent_id`, with the leg's `leg_role`, the parent's `synthetic_type` and its `intent_id`. The table below lists the members that work with parents.

| Member | On | What it does |
|---|---|---|
| `parents` | `TradeableInstrument` | This instrument's parents that have not finished, as a DataFrame |
| `parent(parent_id)` | `TradeableInstrument` | One parent, whether or not it has finished |
| `cancel_parent(parent_id)` | `TradeableInstrument` | Cancels a parent and every leg it still has resting at a broker |
| `parent_orders(parent_id)`, `parent_trades(parent_id)` | `TradeableInstrument` | The parent's rows from the order and trade books |
| `parent_id`, `cancel()`, `parent`, `orders`, `trades` | Every class in `tradingmachine.orders` | The same, for the order the object placed |
| `parents` | `Account` | Every open parent in the account |

A leg of a parent can still be changed with `modify_order` and cancelled with `cancel_order`, and UBI hands the change to the engine so the order type carries on from it. Only a leg's price, trigger price and quantity can change. Cancelling one leg does not stop the parent; `cancel_parent` does.

### Cancelling everything in one instrument

`cancel_open_orders` has to cancel both kinds of waiting order, the ones held in the engine and the ones resting at a broker, without cancelling the same order twice. The numbered steps below are what it does.

1. It reads this instrument's open parents and cancels each with `cancel_parent`. It does this first, because a synthetic order left running could place a new order after its old ones had been cancelled.
2. It reads the instrument's open orders from the order book.
3. It leaves out every order whose `engine_parent_id` is a parent the engine took a cancel for in step 1, because the engine has already dealt with it. An order whose parent's cancel failed, for example because the engine was not running, is kept, so it is still cancelled.
4. It cancels the remaining orders in one request, using the list form of UBI's cancel route.
5. It returns one row per parent and per order, with `cancelled` and `error`, and never raises for one failed cancel.

A parent whose cancel a broker refused for one leg comes back with the state `cancelling` rather than `cancelled`, which UBI answers with HTTP 207. The library returns that answer rather than raising, and `cancel_open_orders` reports such a parent as not cancelled, because one of its legs may still be live.

## Reading an answer later

Every answer to placing an order carries an `intent_id`. When UBI's wait for the engine runs out, the order may still be placed, and `Account.intent(intent_id)` reads what the engine did with it once it has answered. UBI keeps each answer for five minutes by default. The table below lists the three clocks that can run out around an order, and what each raises.

| Clock | Default | What happens | Raised in your program |
|---|---|---|---|
| UBI waiting for its engine, `UNIFIED_BROKER_INTERFACE_API_ORDER_ENGINE_TIMEOUT_SECONDS` | 5 seconds | UBI answers <span class="status s5">504</span> with `outcome: unknown` and the message in `status_message`: `the order engine did not answer within 5.0 seconds, so this order may still be placed` | `OrderOutcomeUnknownError`, whose `detail` carries the `intent_id` to pass to `Account.intent` |
| No engine running at all | none | UBI answers <span class="status s5">503</span> before queueing anything | `ServiceUnavailableError` |
| The client's own wait for any response | 30 seconds per request | No response arrives, and `requests` raises its timeout | `UnreachableError`, chained to the `requests` error |

An engine that restarts reads unfinished intents again. If an intent had already started a parent, UBI answers <span class="status s4">409</span> rather than placing it a second time, which the library raises as `ConflictError`; read the parent for its outcome.

??? note "Under the hood"
    The order routes are called from `TradeableInstrument` in `src/tradingmachine/assets/instruments.py`, through the paths `ORDER_PLACE_PATH`, `ORDER_MODIFY_PATH`, `ORDER_CANCEL_PATH` and `ORDER_PARENTS_PATH`, and from `Account` in `src/tradingmachine/accounts/account.py`, through `PARENTS_PATH` and `INTENT_PATH`. `cancel_open_orders` uses two private helpers, `_cancel_one_parent` and `_cancel_order_list`. The reasoning, including why the old placement-mode check was removed, is in `.claude/notes/src/tradingmachine/assets/instruments.py.md`.

The members involved are documented in the Python API tab: [Orders](../python-api/orders.md), [Price wrappers](../python-api/price-wrappers.md), [Synthetic orders](../python-api/synthetic-orders.md) and [Account](../python-api/account.md). UBI's own page is [Order engine](https://pramodathani.github.io/unified_broker_interface/rest-api/order-engine/).
