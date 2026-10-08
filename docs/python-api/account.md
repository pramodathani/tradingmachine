# The account

Most of the library works on one instrument at a time. `Account` is the exception: it stands for the whole trading account behind UBI, across every broker UBI is connected to, and its three members are the kill switch that empties it, `flatten`, and two readers of UBI's order engine, `parents` and `intent`.

!!! danger "These are real orders"
    `flatten` stops every synthetic order UBI's order engine is running, cancels every open order at every broker, and then sends a real market order to close every open position, in every instrument, with real money. Market orders fill at whatever price is there, and nothing is retried or undone. Always run it with `dry_run=True` first, read what it would do, and send the real call only when you mean it.

The table below lists the class and its members.

| Kind | Member | Description |
|---|---|---|
| <span class="member class">class</span> | [`Account`](#account) | The trading account UBI trades for, across every broker it is connected to. |
| <span class="member writes">places orders</span> | [`flatten`](#flatten) | Stops every synthetic order, cancels every open order at every broker, then closes every position in the account. |
| <span class="member property">property</span> | [`parents`](#parents) | Every synthetic order and held order that UBI's order engine has not finished, in every instrument. |
| <span class="member method">method</span> | [`intent`](#intent) | Reads what UBI's order engine did with one order after its placement stopped waiting for the answer. |

## Account

<div class="endpoint" markdown><span class="member class">class</span> `Account(unified_broker_interface=None)`</div>

An `Account` holds nothing but the client it sends requests through, so constructing one sends no request. By default it takes the same client every instrument uses, from [`Instrument.shared_unified_broker_interface()`](instruments.md#shared_unified_broker_interface). Sharing it means one cached token and one place that reconnects after HTTP 401, whose rules [One token for everyone](client.md#one-token-for-everyone) describes. A caller may still pass a client of its own.

#### Parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `unified_broker_interface` | `UnifiedBrokerInterface` or `None` | no | `None` | The client to use, or `None` to share the one every instrument uses, which is almost always right. |

#### Example

The example below builds an account that shares the instruments' client.

=== "Python"

    ```python
    from tradingmachine.accounts import account

    trading_account = account.Account()
    ```

#### Raises

| Exception | When |
|---|---|
| `ValueError` | No client was given, and the shared client's base URL or MongoDB credentials are not configured. |

## flatten

<div class="endpoint" markdown><span class="member writes">places orders</span> `flatten(confirm, dry_run=False, timeout_seconds=120)`<span class="route"><span class="method post">POST</span> `/api/orders/flatten`</span></div>

This method sends UBI's kill switch. UBI first halts every parent its order engine has not finished, so no armed trigger, trailing stop or grid can place anything afterwards. It then cancels every open order at every broker, waits until the brokers' order books confirm the cancellations, and only then closes every open position, each with a market order on the side that closes it, at the broker that holds it, all at once. Finally it waits again until the brokers' positions show zero before it answers that the account is flat. It acts on the whole account; to close only one instrument's positions, use [`liquidate_all_positions`](positions.md#liquidate_all_positions) on that instrument instead.

You have to type the confirmation word yourself. UBI refuses the request unless its body carries `confirm` set to exactly `FLATTEN`, and the library passes your word through unchecked rather than filling it in, so that one stray `flatten()` call cannot unwind the account.

### Why the cancels go first

The order of the two halves is the whole point. Suppose you hold a long position with a stop-loss order resting below it. If the position were closed first, the stop would still be live at the exchange, and when the price later fell to it, it would sell again and leave you short: a new trade that nobody chose. So UBI cancels first, re-reads the order books every quarter of a second until they agree the orders are gone, and only then sends the closing orders.

The diagram below shows the three middle steps in the order they happen. It leaves out the two steps UBI added on 2026-09-27: before the cancels, UBI halts every open parent in its order engine, and after the closes, it waits up to five more seconds for the brokers' positions to show zero.

<figure class="diagram">
--8<-- "docs/assets/diagrams/flatten.svg"
<figcaption>Orange dots are the request and the cancels, which leave first. Blue dots are UBI re-reading the order books while it waits. Green dots are the closing market orders, which leave only after the wait.</figcaption>
</figure>

#### Parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `confirm` | `str` | yes | | Exactly `FLATTEN`, in capitals. Anything else raises `BadRequestError` and nothing happens. |
| `dry_run` | `bool` | no | `False` | `True` reports what would be cancelled and closed, and sends nothing. The library always sends it as a real JSON boolean, because UBI reads this field with Python's `bool()`, so the string `"false"` would count as a dry run. |
| `timeout_seconds` | `float` | no | `120` | How long to wait for UBI's answer. UBI waits up to five seconds for the cancels, sends the closes to its order engine together, and then waits up to five more seconds for the positions to show zero, so the call can take longer than the client's usual 30 seconds. |

#### Example

The example below previews the kill switch, and then pulls it only if the preview shows something to do. There is no captured output from this project's UBI, because running it for real would empty the account. The outputs are UBI's own recorded answers from its offline suite `test_runs/order_flatten.py`, which runs the route against stubbed brokers, so no real order was involved; that suite records only the names of the `timing_ms` keys, which is why `timing_ms` shows `['preparation']` rather than a number.

=== "Python"

    ```python
    from tradingmachine.accounts import account

    trading_account = account.Account()

    preview = trading_account.flatten(confirm="FLATTEN", dry_run=True)
    print(preview)

    if preview["would_cancel"] or preview["would_close"]:
        outcome = trading_account.flatten(confirm="FLATTEN")
        print(outcome)
        if not outcome["flat"]:
            print("Not flat yet:", outcome["still_open_after_waiting"])
    ```

=== "Output: dry run"

    ```python
    {'dry_run': True,
     'timing_ms': ['preparation'],
     'would_cancel': [{'broker': 'flattrade',
                       'order_id': '26091500000021',
                       'status': 'OPEN'}],
     'would_close': [{'broker': 'flattrade',
                      'close_quantity': 10,
                      'exchange': 'NSE',
                      'instrument_token': '1',
                      'position_key': 'RELIANCE-MIS',
                      'product': 'intraday',
                      'quantity': 10,
                      'segment': None,
                      'tradingsymbol': 'RELIANCE-flattrade',
                      'transaction_type': 'SELL'}]}
    ```

=== "Output: flat"

    ```python
    {'cancelled': [{'broker': 'flattrade',
                    'order_id': '26091500000021',
                    'outcome': 'accepted',
                    'sent': True,
                    'status_message': None}],
     'closed': [{'broker': 'flattrade',
                 'close_quantity': 10,
                 'exchange': 'NSE',
                 'http_status': 200,
                 'instrument_token': '1',
                 'order_id': '26091500000099',
                 'outcome': 'accepted',
                 'position_key': 'RELIANCE-MIS',
                 'product': 'intraday',
                 'quantity': 10,
                 'segment': None,
                 'sent': True,
                 'status_message': None,
                 'tradingsymbol': 'RELIANCE-flattrade',
                 'transaction_type': 'SELL'}],
     'flat': True,
     'halted': {'halted_parents': 0},
     'positions_still_open_after_waiting': [],
     'still_open_after_waiting': [],
     'timing_ms': ['preparation']}
    ```

=== "Output: not flat (HTTP 207)"

    ```python
    {'cancelled': [{'broker': 'flattrade',
                    'order_id': '26091500000021',
                    'outcome': 'accepted',
                    'sent': True,
                    'status_message': None}],
     'closed': [{'broker': 'flattrade',
                 'close_quantity': 10,
                 'exchange': 'NSE',
                 'http_status': 200,
                 'instrument_token': '1',
                 'order_id': '26091500000099',
                 'outcome': 'accepted',
                 'position_key': 'RELIANCE-MIS',
                 'product': 'intraday',
                 'quantity': 10,
                 'segment': None,
                 'sent': True,
                 'status_message': None,
                 'tradingsymbol': 'RELIANCE-flattrade',
                 'transaction_type': 'SELL'}],
     'flat': False,
     'halted': {'halted_parents': 0},
     'positions_still_open_after_waiting': [],
     'still_open_after_waiting': ['flattrade:26091500000021'],
     'timing_ms': ['preparation']}
    ```

=== "Output: position still held (HTTP 207)"

    ```python
    {'cancelled': [],
     'closed': [{'broker': 'flattrade',
                 'close_quantity': 10,
                 'exchange': 'NSE',
                 'http_status': 200,
                 'instrument_token': '1',
                 'order_id': '26091500000099',
                 'outcome': 'accepted',
                 'position_key': 'RELIANCE-MIS',
                 'product': 'intraday',
                 'quantity': 10,
                 'segment': None,
                 'sent': True,
                 'status_message': None,
                 'tradingsymbol': 'RELIANCE-flattrade',
                 'transaction_type': 'SELL'}],
     'flat': False,
     'halted': {'halted_parents': 0},
     'positions_still_open_after_waiting': ['flattrade:RELIANCE-MIS'],
     'still_open_after_waiting': [],
     'timing_ms': ['preparation']}
    ```

The recorded answers are reformatted across lines, and the real runs were re-read from the suite's recording as it stood on 2026-09-27. In the first `flat: False` answer, the broker still reported the cancelled order as live when the five-second wait ran out, so UBI closed the position anyway. In the second, the broker accepted the close but still reported the position when the second wait ended, which can mean the exchange rejected the close after the broker accepted it, or only that the broker's positions had not caught up.

#### Returns

A `dict`, which is UBI's answer unchanged. A dry run returns the keys in the first table below.

| Key | Type | Description |
|---|---|---|
| `dry_run` | `bool` | `True`. |
| `would_cancel` | `list` | Each order that would be cancelled, with `broker`, `order_id` and `status`. |
| `would_close` | `list` | Each position that would be closed, with its broker, product, signed `quantity`, the closing `transaction_type` and the `close_quantity`. |

A real run returns the keys in the table below.

| Key | Type | Description |
|---|---|---|
| `halted` | `dict` | How many of the order engine's open parents were halted before anything was cancelled, under `halted_parents`, or an `error` saying why none could be, such as the engine not running; flatten carries on regardless. |
| `cancelled` | `list` | One entry per cancel attempted, with `broker`, `order_id`, `sent`, `outcome` and `status_message`. |
| `still_open_after_waiting` | `list` of `str` | Orders a broker still reported as live when the wait ended, written as `broker:order_id`. |
| `closed` | `list` | One entry per position, with the position's fields plus `sent`, `outcome`, `order_id`, `http_status` and `status_message`. |
| `positions_still_open_after_waiting` | `list` of `str` | Positions whose close was accepted but which a broker still reported when the second wait ended, written as `broker:position_key`. |
| `flat` | `bool` | `True` only when every cancel was sent, nothing was still open after the wait, every close was sent and accepted, and every closed position showed zero before the second wait ended. |
| `timing_ms` | `dict` | How long UBI took, including every broker call and the wait. |

When any part was not done, UBI answers HTTP 207 rather than an error, so the method returns normally and `flat` is `False`. It deliberately does not raise, because you need the `closed` entries to see what is left. Always check `flat`. UBI's page on the [flatten route](https://pramodathani.github.io/unified_broker_interface/rest-api/flatten/#response-attributes) lists every field and every message an entry can carry.

#### Raises

| Exception | When |
|---|---|
| `BadRequestError` | `confirm` is not exactly `FLATTEN`. |
| `ServiceUnavailableError` | UBI could not read the order books or positions at the start. Nothing was sent. |
| `UnreachableError` | No answer arrived within `timeout_seconds`. Part of the flatten may still have happened. |
| `UnifiedBrokerInterfaceError` | Any other failure reported by, or on the way to, UBI. |

!!! warning "A timeout does not mean nothing happened"
    UBI works through the cancels and the closes, and it carries on after the library has stopped waiting. After an `UnreachableError`, read the orders and positions before you call `flatten` again, or a second flatten may close positions twice.

## What flatten does not do

Two things are outside what the kill switch touches. UBI closed the two larger gaps this page used to list on 2026-09-26 and 2026-09-27: flatten now halts armed synthetic orders first, and each close goes to the broker that holds the position.

1. **A halted parent's position is not handed back.** Halting a parent ends it as `cancelled` without touching its legs, which the cancellations then take care of, and a position it had opened is closed like any other. Nothing restarts the parent afterwards.
2. **Only net positions are closed.** A broker that reports a position both on a day basis and on a net basis would otherwise be closed twice, so UBI closes the net row only.

## Flatten compared with the other ways to close

The library has three ways to close positions, and they differ in reach and in whether they cancel orders first. The table below compares them.

| | [`liquidate_all_positions`](positions.md#liquidate_all_positions) | [`SquareOffOrder`](synthetic-orders.md) | `flatten` |
|---|---|---|---|
| Reach | One instrument | One product, or a chosen list of instruments | The whole account |
| When | Now | At a time of day | Now |
| Cancels resting orders first | :material-close: | :material-check: | :material-check: |
| Closes with | Market or limit orders, your choice | Limit orders | Market orders |
| Needs UBI's order engine | :material-check: | :material-check: | :material-check:, for the halt and the closes |
| Leaves overnight positions alone | :material-close: | :material-check: | :material-close: |

??? note "Under the hood"
    The body is `{"confirm": "<your word>", "dry_run": true or false}`, sent with the shared client's `post` and a per-request timeout of `timeout_seconds`. UBI decides what to cancel and what to close from each broker's own order book and positions in Redis, not from the merged portfolio document. Every order whose status is not `COMPLETE`, `CANCELLED`, `REJECTED` or `EXPIRED` is cancelled, including one with a status UBI does not recognise, because an unknown status is more likely to be a live order than a finished one. UBI's page [What it does, step by step](https://pramodathani.github.io/unified_broker_interface/rest-api/flatten/#what-it-does-step-by-step) follows a real run through every request.

## parents

<div class="endpoint" markdown><span class="member property">property</span> `parents`<span class="route"><span class="method get">GET</span> `/api/orders/parents`</span></div>

This property gives every parent UBI's order engine has not finished, in every instrument. A parent is one order the engine was asked for, such as a bracket, a trailing stop or a limit order it is holding until the book reaches its price. It is the list to read after a flatten or an engine restart, to see what is still working. [`TradeableInstrument.parents`](orders.md#parents) gives one instrument's.

#### Example

The example below prints each open parent's type and state. No output was captured for it.

=== "Python"

    ```python
    frame = trading_account.parents
    if frame is not None:
        print(frame[["parent_order_id", "synthetic_type", "state"]])
    ```

#### Returns

A `pandas.DataFrame` with one row per parent, shaped like [`TradeableInstrument.parents`](orders.md#parents), or `None` when no parent is open.

#### Raises

| Exception | When |
|---|---|
| `ServiceUnavailableError` | UBI's parents could not be read. |
| `UnifiedBrokerInterfaceError` | Any other failure reported by, or on the way to, UBI. |

## intent

<div class="endpoint" markdown><span class="member method">method</span> `intent(intent_id)`<span class="route"><span class="method get">GET</span> `/api/orders/intents/<intent_id>`</span></div>

This method reads what UBI's order engine did with one order after its placement stopped waiting for the answer. Every answer to placing an order carries an `intent_id`, and so does the `detail` of an `OrderOutcomeUnknownError` raised when the engine did not answer within UBI's five-second wait. UBI keeps each answer for five minutes by default after the engine gives it, so read it soon.

#### Parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `intent_id` | `str` | yes | | The `intent_id` from the placement's answer or from the exception's `detail`. |

#### Example

The example below places an order and, when UBI's wait runs out, reads the engine's answer a moment later instead of sending the order again. No output was captured for it, because it places a real order.

=== "Python"

    ```python
    import time

    from tradingmachine.unified_broker_interface import exceptions

    try:
        answer = reliance.buy_at_market_price(quantity=1, product="cnc")
    except exceptions.OrderOutcomeUnknownError as error:
        time.sleep(2)
        stored = trading_account.intent(error.detail["intent_id"])
        answer = stored["response"]
    print(answer["outcome"])
    ```

#### Returns

A `dict` with `intent_id`, the HTTP `status` the placement would have answered with, and the `response` body it would have answered with.

#### Raises

| Exception | When |
|---|---|
| `NotFoundError` | The engine has not answered this intent yet, the id is not one, or its answer has expired. |
| `ServiceUnavailableError` | UBI could not read its store. |
| `UnifiedBrokerInterfaceError` | Any other failure reported by, or on the way to, UBI. |
