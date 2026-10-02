# src/tradingmachine/orders/plan_parts/stages_pricing.py

`StagesPricing` mirrors UBI's `StagesPricing`, in `unified_broker_interface/utilities/order_engine/utilities/stages_pricing.py` in the sibling project, which `PlanReader._read_stages` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` builds. It was written on 2026-10-02 and keeps the rules of UBI's `stepped_stop` synthetic type.

## The JSON shape

```json
{"stages": {"entry_price": 1000.0, "stop_price": 990.0, "limit_offset": 1.0, "step_ticks": 2, "rules": [{"gain": 10.0, "stop_at_gain": 0.0}, {"gain": 25.0, "trail_points": 8.0}]}}
```

`entry_price`, `stop_price`, `limit_offset` and `rules` are required, and the three prices must be above zero. `step_ticks` defaults to 1. The rules are `StageRule` objects, whose limits are in that class's note.

## Naming choice

The `stepped_stop` preset calls the limit distance `stop_limit_offset`; the plan's own `stages` pricing calls it `limit_offset`, as `trail` does, and the class follows the plan.

## Rules that bite

- `stages` is one of UBI's `STOP_PRICINGS`. A stop protects the whole position at once, so an order with it cannot have an execution other than all at once or daily (`stop_not_sliced`), cannot take a `DiscretionModifier` (`discretion_needs_limit`) and cannot take a `PostOnlyGuard` (`post_only_needs_limit`).
- The stop only ever moves in the position's favour, by at least `step_ticks`, so a rule that would loosen it counts as reached and is skipped rather than refused.
- It is usually the `each_fill` child of a `ThenPart` with `side="protect"`, but nothing requires that, because the entry price is stated rather than read from a fill.
