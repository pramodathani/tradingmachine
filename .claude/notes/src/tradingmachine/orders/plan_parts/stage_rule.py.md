# src/tradingmachine/orders/plan_parts/stage_rule.py

`StageRule` is one milestone of a `stages` pricing, the dictionaries that `PlanReader._read_rules` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` reads. UBI has no class for a rule; its `StagesPricing` keeps them as a list of dictionaries. It was written on 2026-10-02 so that the rules of a `StagesPricing` are built from objects like every other part of a plan.

## The JSON shape

```json
{"gain": 10.0, "stop_at_gain": 0.0}
{"gain": 25.0, "trail_points": 8.0}
```

A rule is an entry of a list, so `document()` returns its settings directly rather than under a one-key name, which `PlanPart.document` lists as one of its exceptions.

## Rules that bite

`PlanReader._read_rules` checks the whole list and stops at the first wrong rule, refusing it with `bad_setting`:

- There are 1 to `MOST_RULES`, 20, rules.
- Each `gain` is above zero and larger than the gain of the rule before it.
- Each rule has exactly one of `stop_at_gain` and `trail_points`.
- Only the last rule may have `trail_points`, because trailing hands the rest of the trade over and nothing comes after it.
- `stop_at_gain` may be zero (breakeven) or negative (a smaller loss), but must be below the rule's own `gain`, or the stop would fire at once.

Gains are measured in the position's favour, so the same positive numbers serve a short position as a long one.
