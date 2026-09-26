# The account and its kill switch

!!! danger "`flatten` closes everything in the account"

    It cancels every open order at every broker and closes every position, in every instrument.
    It is the button you press when something has gone wrong. Run it with `dry_run=True` first.

Everything else in the library acts on one instrument. `Account` acts on the whole trading account
UBI trades for, across every broker it is connected to. For now it has one method, `flatten`, which
sends UBI's `POST /api/orders/flatten`.

```python
from tradingmachine.accounts import account

trading_account = account.Account()
preview = trading_account.flatten(confirm="FLATTEN", dry_run=True)
outcome = trading_account.flatten(confirm="FLATTEN")
```

`Account()` shares the client every instrument uses, because UBI holds one access token and a
second client would log the instruments out.

## What it does, in order

The order of the steps is the whole design, so it is worth seeing as a sequence:

1. UBI cancels every open order at every broker.
2. It waits until the brokers' order books confirm the cancellations, or until it gives up waiting.
3. Only then does it close every position, with limit orders.

Closing the positions first would be dangerous. A stop or a target still resting when its position
closes fills afterwards and opens a new position the other way, unattended.

| Argument | What it means |
| --- | --- |
| `confirm` | Must be exactly `"FLATTEN"`. You type it yourself, so a stray call cannot unwind the account |
| `dry_run` | `True` reports what would be cancelled and closed without sending anything |
| `timeout_seconds` | How long to wait for the answer, 120 seconds by default, because UBI cancels and closes one thing after another |

## Reading the answer

| Answer | Keys |
| --- | --- |
| Dry run | `dry_run`, `would_cancel`, `would_close` |
| Real run | `cancelled`, `still_open_after_waiting`, `closed`, `flat`, `timing_ms` |

`flat` is `True` when everything asked for was done. When any part was not, UBI answers with
HTTP 207, which is not an error, so nothing is raised: read `flat`, then `closed` to see which close
failed and why.

## What it cannot promise

!!! warning "Three things `flatten` does not do"

    - **It does not disarm UBI's own synthetic orders** that are waiting for a price or a time, such
      as a hidden stop, a grid or an exposure hedge. Those live in UBI's order engine rather than at a
      broker, so they survive a flatten and can trade again afterwards.
    - **It does not always close a position at the broker holding it.** In engine mode UBI's broker
      selector chooses where each close goes, so check `broker` in each entry of `closed`.
    - **A timeout does not mean nothing happened.** Read the orders and positions before calling it
      again, or a second flatten may close positions twice.

To close only one instrument's positions, use `liquidate_all_positions` on that instrument; see
[Positions](positions.md).
