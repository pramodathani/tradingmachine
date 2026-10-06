# src/tradingmachine/orders/plan_parts/parent_fill_quantity.py

`ParentFillQuantity` mirrors UBI's `FillRatio`, in `unified_broker_interface/utilities/order_engine/utilities/fill_ratio.py` in the sibling project, read by `PlanReader._read_fill_ratio` and checked by `PlanReader._check_fill_sizing` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`. The `attached_hedge` preset uses it with `ratio` and whole lots.

The class is named after the JSON key, `parent_fill`, rather than after UBI's internal class, because the key is what a caller writes.

## The JSON shape

```json
{"parent_fill": {"ratio": 0.5, "whole_lots": true}}
```

`ratio` defaults to 1 in UBI and must be a number above zero; `whole_lots` defaults to false. An empty object, `{"parent_fill": {}}`, is valid and means the whole of what filled. Any other key is refused.

## Rules that bite

- The order must be a `then` join's direct child (`parent_fill_needs_then`): `_check_fill_sizing` refuses any order with a fill ratio that is not `sized_by_fills`, and `_read_then` sets that flag only on an `OrderPart` child.
- With `whole_lots`, a size under one lot of the order's own instrument waits for more fills.
- The child is resized at every fill to `ratio` times the total filled so far, not per fill.

## A child under one lot, and a child on the first plan's instrument (2026-10-06)

UBI's commit `15380c1` of 2026-10-05 cancels a child whose size is still under one lot once the first plan has finished, where before it left the parent `working` for ever. The same commit refuses with HTTP 400 a child sized this way that names an instrument the first plan trades, because it would only trade back what was filled.
