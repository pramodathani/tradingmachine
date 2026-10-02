# src/tradingmachine/orders/plan_parts/sequence_part.py

`SequencePart` mirrors UBI's `SequencePart`, in `unified_broker_interface/utilities/order_engine/utilities/sequence_part.py` in the sibling project, read by `PlanReader._read_sequence` and `PlanReader._read_children` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`.

## The JSON shape

```json
{"sequence": {"children": [{"order": {}}, {"order": {}}]}}
```

`children` is the only key UBI takes (`SEQUENCE_SETTINGS`), and it must hold 2 to 25 plans; one child is refused as `join_shape`. The class therefore has a single keyword-only parameter.

## Rules that bite

- A child starts only once the one before it is done, whether it filled or ended, so a child that never fills and has no lifetime holds every later child back indefinitely. Give a waiting child a `Lifetime` when that matters.
- A sequence join cannot be a `then` join's child (`join_not_sized`).
- Children can be joins themselves, such as a `then` join holding an entry and its exits, which is how the example in `examples/orders/plan_parts/sequence_part/sequence_part/protected_trade_then_afternoon_reentry.py` runs a second trade only after the first is over.
