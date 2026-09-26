# The account

Most of the library works on one instrument at a time. `Account` is the exception: it stands for the whole trading account behind UBI, across every broker UBI is connected to, and its one member, `flatten`, is the kill switch that empties it.

!!! danger "These are real orders"
    `flatten` cancels every open order at every broker and then sends a real market order to close every open position, in every instrument, with real money. Market orders fill at whatever price is there, and nothing is retried or undone. Always run it with `dry_run=True` first, read what it would do, and send the real call only when you mean it.

The table below lists the class and its member.

| Kind | Member | Description |
|---|---|---|
| <span class="member class">class</span> | [`Account`](#account) | The trading account UBI trades for, across every broker it is connected to. |
| <span class="member writes">places orders</span> | [`flatten`](#flatten) | Cancels every open order at every broker, then closes every position in the account. |

## Account

<div class="endpoint" markdown><span class="member class">class</span> `Account(unified_broker_interface=None)`</div>

An `Account` holds nothing but the client it sends requests through, so constructing one sends no request. By default it takes the same client every instrument uses, from [`Instrument.shared_unified_broker_interface()`](instruments.md#shared_unified_broker_interface). That matters, because UBI holds a single access token for the whole application and every `connect` replaces it: an `Account` with a client of its own would log every instrument out on its first request.

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

This method sends UBI's kill switch. UBI cancels every open order at every broker, waits until the brokers' order books confirm the cancellations, and only then closes every open position, each with a market order on the side that closes it. It acts on the whole account; to close only one instrument's positions, use [`liquidate_all_positions`](positions.md#liquidate_all_positions) on that instrument instead.

You have to type the confirmation word yourself. UBI refuses the request unless its body carries `confirm` set to exactly `FLATTEN`, and the library passes your word through unchecked rather than filling it in, so that one stray `flatten()` call cannot unwind the account.

### Why the cancels go first

The order of the two halves is the whole point. Suppose you hold a long position with a stop-loss order resting below it. If the position were closed first, the stop would still be live at the exchange, and when the price later fell to it, it would sell again and leave you short: a new trade that nobody chose. So UBI cancels first, re-reads the order books every quarter of a second until they agree the orders are gone, and only then sends the closing orders.

The diagram below shows the three steps in the order they happen.

<figure class="diagram">
--8<-- "docs/assets/diagrams/flatten.svg"
<figcaption>Orange dots are the request and the cancels, which leave first. Blue dots are UBI re-reading the order books while it waits. Green dots are the closing market orders, which leave only after the wait.</figcaption>
</figure>

#### Parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `confirm` | `str` | yes | | Exactly `FLATTEN`, in capitals. Anything else raises `BadRequestError` and nothing happens. |
| `dry_run` | `bool` | no | `False` | `True` reports what would be cancelled and closed, and sends nothing. The library always sends it as a real JSON boolean, because UBI reads this field with Python's `bool()`, so the string `"false"` would count as a dry run. |
| `timeout_seconds` | `float` | no | `120` | How long to wait for UBI's answer. UBI waits up to five seconds for the cancels and then closes the positions one after another, so an account with several positions can take longer than the client's usual 30 seconds. |

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
     'still_open_after_waiting': ['flattrade:26091500000021'],
     'timing_ms': ['preparation']}
    ```

The recorded answers are reformatted across lines. In the last one, the broker still reported the cancelled order as live when the five-second wait ran out, so UBI closed the position anyway and answered `flat: False`.

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
| `cancelled` | `list` | One entry per cancel attempted, with `broker`, `order_id`, `sent`, `outcome` and `status_message`. |
| `still_open_after_waiting` | `list` of `str` | Orders a broker still reported as live when the wait ended, written as `broker:order_id`. |
| `closed` | `list` | One entry per position, with the position's fields plus `sent`, `outcome`, `order_id`, `http_status` and `status_message`. |
| `flat` | `bool` | `True` only when every cancel was sent, nothing was still open after the wait, and every close was sent and accepted. |
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
    UBI works through the cancels and closes one after another, and it carries on after the library has stopped waiting. After an `UnreachableError`, read the orders and positions before you call `flatten` again, or a second flatten may close positions twice.

## What flatten does not do

Three things are outside what the kill switch touches, and each can surprise you. The first two are gaps in UBI rather than in the library, so they can only be fixed there.

1. **Armed synthetic orders survive it.** A hidden stop, a grid, an exposure hedge or any other [synthetic order](synthetic-orders.md) that is waiting inside UBI's order engine for a price or a time is not a broker order, so flatten neither sees nor disarms it. Such an order can trade again after the account is flat, and UBI has no REST route yet to list or cancel one.
2. **In engine mode, UBI chooses where each close goes.** With UBI's order engine running, which is how this library expects UBI to run, each close is sent as a plain order and UBI's broker selector picks the broker, rather than the broker that holds the position. Check `broker` in each `closed` entry against where you expected it.
3. **Only net positions are closed.** A broker that reports a position both on a day basis and on a net basis would otherwise be closed twice, so UBI closes the net row only.

!!! note "Market orders, not limit orders"
    UBI's code sends every closing order with `order_type` `MARKET`, and UBI's own documentation says the same. The library's docstring for `flatten` says the positions are closed with limit orders, which is not what UBI does.

## Flatten compared with the other ways to close

The library has three ways to close positions, and they differ in reach and in whether they cancel orders first. The table below compares them.

| | [`liquidate_all_positions`](positions.md#liquidate_all_positions) | [`SquareOffOrder`](synthetic-orders.md) | `flatten` |
|---|---|---|---|
| Reach | One instrument | One product, or a chosen list of instruments | The whole account |
| When | Now | At a time of day | Now |
| Cancels resting orders first | :material-close: | :material-check: | :material-check: |
| Closes with | Market or limit orders, your choice | Limit orders | Market orders |
| Needs UBI's order engine | :material-check: | :material-check: | :material-close: |
| Leaves overnight positions alone | :material-close: | :material-check: | :material-close: |

??? note "Under the hood"
    The body is `{"confirm": "<your word>", "dry_run": true or false}`, sent with the shared client's `post` and a per-request timeout of `timeout_seconds`. UBI decides what to cancel and what to close from each broker's own order book and positions in Redis, not from the merged portfolio document. Every order whose status is not `COMPLETE`, `CANCELLED`, `REJECTED` or `EXPIRED` is cancelled, including one with a status UBI does not recognise, because an unknown status is more likely to be a live order than a finished one. UBI's page [What it does, step by step](https://pramodathani.github.io/unified_broker_interface/rest-api/flatten/#what-it-does-step-by-step) follows a real run through every request.
