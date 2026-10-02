# src/tradingmachine/orders/plan_parts/from_fill_pricing.py

`FromFillPricing` mirrors UBI's `FromFillPricing`, in `unified_broker_interface/utilities/order_engine/utilities/from_fill_pricing.py` in the sibling project, which `PlanReader._read_from_fill` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` builds. It was written on 2026-10-02. UBI added it the same day so that the exits of `two_sided_breakout` could be distances from the fill rather than absolute prices; the reasoning is in `.claude/notes/src/tradingmachine/orders/two_sided_breakout.py.md`.

## The JSON shape

```json
{"from_fill": {"stop_distance": 10.0, "stop_limit_offset": 1.0}}
{"from_fill": {"target_distance": 20.0}}
```

A stop takes `stop_distance` and `stop_limit_offset` together, and a target takes `target_distance` alone; each value must be above zero. Giving both kinds, or neither, is refused with `bad_setting` or `missing_setting`. The class takes all three as optional keywords and sends whichever are set, leaving the choice to UBI as the spec requires.

## Rules that bite

- The order must sit under a `ThenPart`'s `each_fill` or `on_complete` child, directly or inside an `EitherPart` there, because the price comes from the fill that opened the position. Anywhere else `PlanReader._check_fill_sizing` refuses it with `from_fill_needs_then`.
- The direction comes from the side the exit is sent on: a selling exit's stop sits below the fill and its target above, and a buying exit's the other way round. One plan therefore protects a position opened either way, which is why it suits a two-sided breakout.
- A stop form is a native stop-limit, so like the `STOP_PRICINGS` it cannot be split into pieces (`stop_not_sliced`).
