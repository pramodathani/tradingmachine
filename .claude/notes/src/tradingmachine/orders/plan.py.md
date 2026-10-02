# src/tradingmachine/orders/plan.py

`PlanOrder` is the library's side of UBI's `plan` synthetic order type, the start of what UBI calls composable synthetic orders. On 2026-10-01 the user asked for one order type, or a handful, that could build any existing synthetic order from parameters and also combine whole types with each other. Order logic lives in UBI, so the user handed that design to a session in `../unified_broker_interface`, which built it as the `plan` type, and asked for a class here "just like we have synthetic order classes right now".

The class is deliberately as thin as every other order class: it is a `SyntheticOrder` whose only setting is `plan`, the root part of a tree, and `synthetic_fields()` returns that root's `document()`. Nothing is checked locally, because UBI's `PlanReader` checks the whole plan and lists every problem with the path of the part it is in, which is better than anything a local check could say.

## How the tree is written

The user was offered two shapes, plain dicts written exactly as UBI documents them, or one small class per part, and had no preference, so the recommended one was taken: one class per part, in `src/tradingmachine/orders/plan_parts/`. The classes read much better than nested dicts and give the editor something to complete, at the cost of keeping fifteen classes in step with UBI as the plan format grows. `Preset` is the exception, taking any name and any settings, because UBI means to turn every one of the other types into a preset and a class per preset would have to follow each of those additions.

## State of UBI when this was written

UBI merged stages one to three on 2026-10-01, as pull request #31 into its `main`: the order part with triggers, `protect` and pricing, the `then` and `either` joins, and thirteen presets (`simple`, `market_if_touched`, `limit_if_touched`, `scheduled`, `indicator_triggered`, `cross_instrument`, `hidden_stop`, `trailing_stop`, `trailing_entry`, `oto`, `oco`, `bracket`, `cover`). The joins `together`, `using`, `repeat` and `sequence` are reserved names that UBI refuses as not built yet, so they have no class here; each needs a class in `plan_parts` once UBI builds it.

Every plan built by the docstring examples was checked against UBI's own `PlanReader` from the branch before it was merged, and all of them were read without a problem, including the two preset combinations, where UBI turns `market_if_touched` plus `bracket` into a `then` join.

## The lower-case side bug in UBI

On 2026-10-01 the plan engine read the template's `transaction_type` straight from the stored body and compared it with `'BUY'` and `'SELL'`. This library sends `"buy"` and `"sell"`, which UBI stores as given, so for a plan sent from here a `price_crosses` trigger with no direction was read the wrong way round (a buy waited for a rise and fired at once), and a `protect` order failed, because `OPPOSITE_SIDES` only has upper-case keys. UBI's other types upper-case the side before using it. It is left for UBI to fix rather than worked around here, because upper-casing in `PlanOrder` alone would hide a bug that every other caller of UBI would still hit. Until UBI fixes it, give every `PriceCrosses` an explicit `direction`, and do not run the `PlanOrder` example programs.
