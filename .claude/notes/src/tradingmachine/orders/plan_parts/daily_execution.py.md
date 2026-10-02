# src/tradingmachine/orders/plan_parts/daily_execution.py

`DailyExecution` mirrors UBI's `DailyExecution` in `unified_broker_interface/utilities/order_engine/utilities/daily_execution.py` in the sibling project, read through `PlanReader._read_daily` in `plan_reader.py`, as of 2026-10-02. It is the plan's form of the fixed `daily_stop` type.

Its JSON is `{"daily": {"arm_at": "09:30"}}`, or `{"daily": {}}` for UBI's default `arm_at` of `09:20`, which the class sends by leaving `arm_at` out when None. UBI refuses a value that is not a time `HH:MM` with hours under 24 and minutes under 60.

## Behaviour

A native stop dies at the close, so the order is sent again each trading day at `arm_at`, after the pre-open has settled, and not on a day the instrument does not trade. A plan placed after that time, or on a non-trading day, first sends on the next trading morning. The day last sent is recorded with the order, so a restart does not send twice. Once anything trades no more is sent. UBI's commit `9731fa9` of 2026-10-02 fixed the case where a stop that had traded re-armed the next morning, or sold at once below the stop; the parent now completes instead.

UBI's documentation says to pair it with a lifetime in `after_days`, which ends it and keeps the plan across days, so `stop_renewed_each_morning.py` uses `Lifetime(after_days=5)`.

## Rules that bite

`daily` is one of only two executions a resting stop may have, the other being `all_at_once`, because renewing a stop whole each morning still protects the whole position at once. Every other execution with `native_stop`, `trail`, `stages` or a stop `from_fill` pricing is refused as `stop_not_sliced`; `sliced_stop_refused.py` shows the three cases. It is in neither nesting list.
