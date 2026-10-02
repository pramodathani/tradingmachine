# src/tradingmachine/orders/plan_parts/discretion_modifier.py

`DiscretionModifier` mirrors UBI's `DiscretionModifier`, in `unified_broker_interface/utilities/order_engine/utilities/discretion_modifier.py` in the sibling project, which `PlanReader._read_discretion` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` builds. It was written on 2026-10-02 and keeps the rules of UBI's `discretionary` synthetic type.

## The JSON shape

```json
{"discretion": {"points": 0.25, "quantity": 40}}
```

`points` is required and must be above zero; `quantity` is optional, at least 1, and defaults to everything still resting. The synthetic type calls these `discretion_points` and `discretion_quantity`; the plan's names are used here.

## Where it goes

Like the cap, it is a modifier read from the `pricing` list beside the one setter, so it is passed as `OrderPart(pricing=..., discretion=...)`. A second discretion in one list is refused with `two_discretions`. With no setter at all, the template's own order type and price are used.

## Rules that bite

`PlanReader._can_take_at_discretion` needs one visible limit:

- On a stop, any of the `STOP_PRICINGS` `native_stop`, `trail`, the average-true-range trail and `stages`, it is refused with `discretion_needs_limit`.
- With any execution other than all at once, it is refused with `discretion_not_sliced`.

The taking order is a limit `BUFFER_TICKS`, two ticks, past the other side's touch, never past the visible price plus `points`, and the visible order is reduced or cancelled before it is sent, so the two can never both fill in full.
