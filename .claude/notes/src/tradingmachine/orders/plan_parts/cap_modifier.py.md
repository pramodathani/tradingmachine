# src/tradingmachine/orders/plan_parts/cap_modifier.py

`CapModifier` mirrors UBI's `CapModifier`, in `unified_broker_interface/utilities/order_engine/utilities/cap_modifier.py` in the sibling project, which `PlanReader._read_cap` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` builds. It was written on 2026-10-02.

## The JSON shape

```json
{"cap": {"worst_price": 1010.0}}
```

`worst_price` is required and must be above zero.

## Where it goes

A cap is a modifier, not a pricing setter. UBI reads it from the same `pricing` list as the setter, and `PlanReader._read_pricing_list` sorts the entries into one setter, one cap and one discretion. The class is therefore passed as `OrderPart(pricing=..., cap=...)`, and `OrderPart.document` puts it in the `pricing` list after the setter. A second cap in one list is refused with `two_caps`; a cap from a preset and another from the order itself is a replacement, reported as a warning.

## Rules that bite

- The cap holds for a buy as the most it pays and for a sell as the least it takes; the same class serves both.
- It replaces the `cap_price` setting of the `peg` and `chaser` synthetic types, which in a plan is no longer part of the pricing itself.
- A market order has no limit to cap, so a cap beside a `MARKET` `FixedPricing` has no effect.
