# src/tradingmachine/orders/plan_parts/parent_fill_delta_quantity.py

`ParentFillDeltaQuantity` mirrors UBI's `FillDelta`, in `unified_broker_interface/utilities/order_engine/utilities/fill_delta.py` in the sibling project, read by `PlanReader._read_fill_delta` and paired with the side in `PlanReader._read_order` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`. The `attached_hedge` preset uses it when given `delta_volatility`.

## The JSON shape

```json
{"parent_fill_delta": {"volatility": 12.5, "whole_lots": true}}
```

`volatility` is required, a percentage above zero, so the constructor has no default for it. `whole_lots` defaults to false. Any other key is refused.

## Rules that bite

- The order's side must be `against_delta`, and an `against_delta` side must have this quantity (`against_delta_needs_delta`). That side is opposite the opening side for a call and the same side for a put.
- Like `parent_fill`, it is only for a `then` join's direct child (`parent_fill_needs_then`).
- UBI takes the Black-76 delta of the plan's own instrument, which must be an option or the plan is refused with HTTP 400 when placed, using the last price of this order's instrument, usually the future, as the forward. The offline `PlanReader` cannot see the instrument, so that check happens only at placing.
- An expired option, or a forward with no price, leaves the size as it was.

## A forward with no price is tried again (2026-10-06)

UBI's commit `15380c1` of 2026-10-05 tries a delta hedge whose forward has no price again on every tick until the order has started, rather than leaving it unsized, and refuses with HTTP 400 a child sized this way that names an instrument the first plan trades. As with `ParentFillQuantity`, a size under one lot is cancelled once the first plan has finished.
