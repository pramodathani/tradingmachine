# src/tradingmachine/orders/plan_parts/follow_instrument_pricing.py

`FollowInstrumentPricing` mirrors UBI's `FollowInstrumentPricing`, in `unified_broker_interface/utilities/order_engine/utilities/follow_instrument_pricing.py` in the sibling project, which `PlanReader._read_follow_instrument` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` builds. It was written on 2026-10-02 and keeps the rules of UBI's `underlying_peg` synthetic type.

## The JSON shape

```json
{"follow_instrument": {"instrument_id": "dba60324-...", "delta": 0.5, "lowest": 125.6, "highest": 188.3, "step_ticks": 2}}
```

`instrument_id` and `delta` are required. `delta` is any finite number, so a negative delta for a put is accepted. `lowest` and `highest` must be above zero, and `lowest` may not be above `highest`. `step_ticks` defaults to 1.

## Naming choice

The class takes an instrument object rather than an id string, the same as `PriceCrosses`, and sends its `instrument_id`. The synthetic type calls the same field `watch_instrument_id` and its bounds `lowest_price` and `highest_price`; in a plan they are `instrument_id`, `lowest` and `highest`, and the class follows the plan's names.

## Rules that bite

- The price starts at the template's own limit price, so the `PlanOrder` must be a `limit` order with a `price`, and the followed instrument must be another one than the order's own. Both are checked only when the plan is placed, with HTTP 400; the offline `PlanReader` does not check them.
- Nothing in the plan says which instrument the order trades except the `PlanOrder` or the `OrderPart`'s own `instrument`, so the examples build a `PlanOrder` on a real Nifty option without placing it.
