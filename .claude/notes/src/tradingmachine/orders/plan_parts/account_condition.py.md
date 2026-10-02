# src/tradingmachine/orders/plan_parts/account_condition.py

`AccountCondition` mirrors UBI's `AccountCondition`, in `unified_broker_interface/utilities/order_engine/utilities/account_condition.py` in the sibling project, read by `PlanReader._read_account` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`. It keeps the rules of the `account_conditional` synthetic type, whose preset builds this condition either as a trigger or, with `action: cancel`, as a lifetime's `when`.

The module is named `account_condition` rather than `account` so it does not clash in reading with `tradingmachine.accounts.account`; the class name matches UBI's.

## The JSON shape

```json
{"account": {"field": "day_pnl", "level": -5000.0, "direction": "at_or_below"}}
```

All three settings are required, which is why the constructor has no defaults. Any other key is refused.

| `field` | What UBI reads |
|---|---|
| `available_balance` | `summary.available_balance` of the funds document in Redis under `unified:portfolio:funds`, the free margin across every broker |
| `day_pnl` | `pnl.realized` plus `pnl.unrealized` of the same document, across every broker |
| `open_positions` | The count of net positions with a non-zero quantity across every broker |

`level` is any finite number, so a negative level for a day's loss and 0 for "no positions open" are both accepted. `direction` must be `at_or_above` or `at_or_below`; UBI requires it because nothing about an order says which way an account figure should move.

## Rules that bite

- It reads no quotes, so the engine checks it once a second on the clock rather than on ticks.
- When the figure cannot be read, for example when Redis has no funds document, the condition simply does not hold, so an order waiting on it waits rather than firing.
- The figures are account-wide, not per instrument, so a plan on one share can be gated by losses on another.
