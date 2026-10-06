# src/tradingmachine/orders/plan_parts/from_parent_fill_pricing.py

`FromParentFillPricing` mirrors UBI's `FromParentFillPricing`, in `unified_broker_interface/utilities/order_engine/utilities/from_parent_fill_pricing.py` in the sibling project, which `PlanReader._read_setter` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` builds inline (there is no `_read_from_parent_fill`). It was written on 2026-10-02 and keeps the arithmetic of UBI's `legged_spread` synthetic type.

## The JSON shape

```json
{"from_parent_fill": {"net_price": 45.0}}
```

`net_price` is required and is read with `_number`, not `_price`, so it may be zero or negative: positive is a net debit, negative a credit. No other key is accepted.

## Rules that bite

- The order must be the child of a `ThenPart` whose `first` plan is a single order, because the price is worked out from that order's average fill. Anywhere else `PlanReader._check_fill_sizing` refuses it with `from_parent_fill_needs_then`.
- The first leg's side signs its fill and the second leg's side signs the result, so the second leg is usually the opposite side and often another instrument, given through `OrderPart(instrument=..., transaction_type=...)`.
- A worked-out price at or below zero cannot be sent, so the order waits rather than failing.

## Each order priced to the running average (2026-10-06)

UBI's commit `cfdcad7` of 2026-10-05 changed how the second leg is priced. It used to be priced from the first leg's cumulative average alone, so each top-up priced from an earlier average left the spread away from `net_price`, 20.65 against 20 in one of UBI's runs. Each new order is now priced so that the second leg's orders together average what the net needs, and rounded to the second leg's tick in the caller's favour, down for a buy and up for a sell; before, a price such as 982.05 on a 0.10 tick was refused by the broker and the refusal was lost.
