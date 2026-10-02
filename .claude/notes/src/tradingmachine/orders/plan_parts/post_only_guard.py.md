# src/tradingmachine/orders/plan_parts/post_only_guard.py

`PostOnlyGuard` mirrors UBI's `PostOnlyGuard`, in `unified_broker_interface/utilities/order_engine/utilities/post_only_guard.py` in the sibling project, which `PlanReader._read_guards_list` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` builds. It was written on 2026-10-02 and keeps the rules of UBI's `post_only` synthetic type.

## The JSON shape

```json
{"post_only": {"on_crossing": "rest"}}
```

`on_crossing` is optional, one of UBI's `ON_CROSSING`, `refuse` (the default) or `rest`. `post_only` is the only guard UBI has built, so any other key in the `guards` list is refused with `unknown_guard`. `OrderPart.document` wraps the guard in a list of one under `guards`.

## Rules that bite

`PlanReader._can_rest` refuses the guard beside pricing that cannot rest:

- On a stop, any of the `STOP_PRICINGS`, with `post_only_needs_limit`.
- Beside pricing that means to trade at once, with `post_only_crosses`: `MarketablePricing`, `ChasePricing`, a `PegPricing` with `reference="opposite_touch"`, or a `FixedPricing` with `order_type="MARKET"`.

With `refuse`, a crossing limit ends the order, and when that is the plan's first order the placement answers HTTP 409. Indian exchanges have no post-only flag, so the book can still move while the order is in flight; the guard is an approximation.
