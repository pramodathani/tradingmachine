# src/tradingmachine/orders/plan_parts/twap_execution.py

`TwapExecution` mirrors UBI's `TwapExecution` in `unified_broker_interface/utilities/order_engine/utilities/twap_execution.py` in the sibling project, whose schedule is in `timed_slices_execution.py`. It is read by `PlanReader._read_timed` in `plan_reader.py`, as of 2026-10-02.

Its JSON is `{"twap": {"slices": 6, "over_minutes": 60}}`. Both are required. `slices` is a whole number from 2 to 60, the 60 being `MOST_SLICES` in `plan_reader.py`, and `over_minutes` is a number above zero. Unlike VWAP, TWAP does not accept `until`; UBI refuses it as `unknown_setting`.

## Behaviour

One slice goes every `over_minutes × 60 / slices` seconds, the first at once. Quantities are shared with the largest-remainder method, so equal weights give an exact even split with the leftover units going to the earliest slices. Each slice is sized from the order's total when it falls due, so a join that changes the total spreads the change over the slices still to come, and the last slice sends what is left. A slice that has not filled is left resting when the next goes. TWAP is paced by ticks, so the order starts working as soon as its trigger holds.

A pricing that moves its order, such as a peg, moves every slice still resting.

## Nesting and other joins

TWAP is in both of UBI's nesting lists, so it can be the outer execution, with an inner `iceberg`, `vwap`, `front_loaded` or another `twap`, or the inner one under `participation`, `iceberg`, `vwap`, `front_loaded` or `twap`. It is also one of the three executions, with `ladder` and `front_loaded`, that a `using` join accepts, because its pieces are known in advance.

## Rules that bite

A resting stop cannot be sliced, so TWAP with `native_stop`, `trail` or `stages` pricing is refused as `stop_not_sliced`.
