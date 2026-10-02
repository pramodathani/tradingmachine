# src/tradingmachine/orders/plan_parts/all_at_once_execution.py

`AllAtOnceExecution` mirrors UBI's `AllAtOnceExecution` in `unified_broker_interface/utilities/order_engine/utilities/all_at_once_execution.py` in the sibling project, and the `all_at_once` branch of `PlanReader._read_execution_value` in `plan_reader.py`, read on 2026-10-02.

Its JSON is `{"all_at_once": {}}`, an entry of the order's `execution` list, which `OrderPart` builds. UBI refuses any setting inside the empty object as `unknown_setting`.

## Why a class for UBI's default

An order with no execution is already sent all at once, because `PlanReader` fills in `AllAtOnceExecution()` when the order names none. The class exists for two cases. A later value replaces an earlier one, so an order's own `execution=AllAtOnceExecution()` overrides an execution that a preset gave, with UBI's `execution_replaced` warning; the example `replace_a_preset_execution.py` shows this. And it lets a stop say explicitly that it is sent whole.

## Rules that bite

- A resting stop, meaning `native_stop`, `trail` (with or without its `atr` object) or `stages` pricing, or `from_fill` pricing set up as a stop, may only have `all_at_once` or `daily` execution. Anything else is refused as `stop_not_sliced`, because a stop protects the whole position at once.
- Under a join that resizes the order, such as a `ThenPart` `each_fill` child, `all_at_once` modifies its one resting order rather than sending another. `TopUpExecution` is the alternative that keeps each order's queue place.
- It is neither in `NESTED_OUTER_NAMES` nor `NESTED_INNER_NAMES`, so it cannot be one half of a nested pair.
