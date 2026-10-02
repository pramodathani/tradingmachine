# src/tradingmachine/orders/plan_parts/front_loaded_execution.py

`FrontLoadedExecution` mirrors UBI's `FrontLoadedExecution` in `unified_broker_interface/utilities/order_engine/utilities/front_loaded_execution.py` in the sibling project, on the shared clock of `timed_slices_execution.py`. It is read by `PlanReader._read_timed` in `plan_reader.py`, as of 2026-10-02. It is the plan's form of the fixed `implementation_shortfall` type.

Its JSON is `{"front_loaded": {"slices": 5, "over_minutes": 30, "urgency": 0.8}}`. `slices` runs from 2 to 60, `over_minutes` must be above zero, and `urgency` is a number from 0 to 1 that defaults to 0.5 in UBI, so the class leaves it out when None. It does not accept `until`.

## Behaviour

Slices go on the TWAP clock, but each is `1 - urgency × 0.5` of the one before. An urgency of 0 is an even split, 0.5 makes each slice three quarters of the last, and 1 halves every slice. The `compare_urgencies.py` example prints the approximate sizes; UBI's own sizes use the largest-remainder method and may differ by a unit.

## Nesting and other joins

It is in both nesting lists, so it can be outer or inner, and it is one of the three executions a `using` join accepts.

## Rules that bite

A resting stop cannot be sliced, so stop pricing with this execution is refused as `stop_not_sliced`.
