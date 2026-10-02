# src/tradingmachine/orders/plan_parts/chase_pricing.py

`ChasePricing` mirrors UBI's `ChasePricing`, in `unified_broker_interface/utilities/order_engine/utilities/chase_pricing.py` in the sibling project, which `PlanReader._read_chase` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` builds. It was written on 2026-10-02 and keeps the rules of UBI's `chaser` synthetic type.

## The JSON shape

```json
{"chase": {"step_ticks": 1, "step_seconds": 5, "cross_after_seconds": 60}}
```

Every key is optional. `step_ticks` defaults to 1 and must be a whole number of at least 1; `step_seconds` defaults to 5 and must be a number above zero; `cross_after_seconds` has no default, and when it is given it must be above zero too.

## Rules that bite

- The chaser type's `cap_price` is not a chase setting in a plan. It is a separate `CapModifier` beside the chase, as `OrderPart(pricing=ChasePricing(...), cap=CapModifier(...))`, and the cap holds every step.
- A chase means to trade against the other side, so `PlanReader._can_rest` refuses it beside a `PostOnlyGuard` with `post_only_crosses`.
- The chase's clock is kept in the pricing's memory and recorded with each step, so a restart of UBI's engine neither steps at once nor forgets when the chase began. When a caller changes the price, the chase waits a full step before moving again.
