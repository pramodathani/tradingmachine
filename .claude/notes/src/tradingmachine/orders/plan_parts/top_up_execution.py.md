# src/tradingmachine/orders/plan_parts/top_up_execution.py

`TopUpExecution` mirrors UBI's `TopUpExecution` in `unified_broker_interface/utilities/order_engine/utilities/top_up_execution.py` in the sibling project, and the `top_up` branch of `PlanReader._read_execution_value` in `plan_reader.py`, as of 2026-10-02.

Its JSON is `{"top_up": {}}`, and UBI refuses any setting inside it as `unknown_setting`.

## What it is for

It only makes sense for an order whose size a join changes, such as the `each_fill` child of a `ThenPart`. Each time the target grows, one new broker order is sent for the quantity neither traded nor resting, so every broker order keeps the price it was given and its place in the queue; the default `all_at_once` would modify its one resting order instead. A target that shrinks cuts resting orders, newest first. A cancelled order's unfilled part is sent again, and a rejection stops it.

UBI's `attached_hedge` and `legged_spread` presets use it for their second leg, which is why the example `calendar_spread_legged_in.py` writes a legged calendar spread out with it.

## Rules that bite

It is in neither nesting list, and a resting stop cannot use it, since a stop may only be `all_at_once` or `daily`.
