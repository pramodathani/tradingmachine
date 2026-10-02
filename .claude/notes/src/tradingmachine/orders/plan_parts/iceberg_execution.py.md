# src/tradingmachine/orders/plan_parts/iceberg_execution.py

`IcebergExecution` mirrors UBI's `IcebergExecution` in `unified_broker_interface/utilities/order_engine/utilities/iceberg_execution.py` in the sibling project, read through `PlanReader._read_iceberg` in `plan_reader.py`, as of 2026-10-02.

Its JSON is `{"iceberg": {"visible_quantity": 10, "randomise_percent": 20}}`. `visible_quantity` is a whole number of at least 1 and is required. `randomise_percent` is a whole number from 0 to 99 and defaults to 0 in UBI, so it is left out when None. Any other key is refused as `unknown_setting`.

## Behaviour

One piece is sent at a time and the next only once the last has filled. The variation of each piece is worked out from the parent's id and the number of pieces sent, so it is repeatable after a restart but does not form a visible pattern. A piece that is cancelled or rejected stops the iceberg, because whoever stopped it meant the order to stop.

The fixed type `iceberg` calls the same setting `slice_quantity`; the plan's execution calls it `visible_quantity`, and the class follows the plan.

## Nesting

`iceberg` is the only execution in both of UBI's lists in `nested_execution.py`: `OUTER_NAMES` is `twap`, `vwap`, `front_loaded`, `participation`, `iceberg`, and `INNER_NAMES` is `iceberg`, `twap`, `vwap`, `front_loaded`. So it can show each slice of another execution a little at a time, which is the common use, as in `OrderPart(execution=TwapExecution(...), inner_execution=IcebergExecution(...))`, sent as `"execution": [{"twap": ...}, {"iceberg": ...}]`. It can also release its own pieces as slices for an inner timed execution to work. Pairs outside those lists are refused as `bad_nesting`, and a third value as `nesting_too_deep`.

## Rules that bite

A resting stop cannot be an iceberg; UBI refuses it as `stop_not_sliced`.
