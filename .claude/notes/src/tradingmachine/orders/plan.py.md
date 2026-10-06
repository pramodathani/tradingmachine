# src/tradingmachine/orders/plan.py

`PlanOrder` is the library's side of UBI's `plan` synthetic order type, the start of what UBI calls composable synthetic orders. On 2026-10-01 the user asked for one order type, or a handful, that could build any existing synthetic order from parameters and also combine whole types with each other. Order logic lives in UBI, so the user handed that design to a session in `../unified_broker_interface`, which built it as the `plan` type, and asked for a class here "just like we have synthetic order classes right now".

The class is deliberately as thin as every other order class: it is a `SyntheticOrder` whose only setting is `plan`, the root part of a tree, and `synthetic_fields()` returns that root's `document()`. Nothing is checked locally, because UBI's `PlanReader` checks the whole plan and lists every problem with the path of the part it is in, which is better than anything a local check could say.

## How the tree is written

The user was offered two shapes, plain dicts written exactly as UBI documents them, or one small class per part, and had no preference, so the recommended one was taken: one class per part, in `src/tradingmachine/orders/plan_parts/`. The classes read much better than nested dicts and give the editor something to complete, at the cost of keeping fifteen classes in step with UBI as the plan format grows. `Preset` is the exception, taking any name and any settings, because UBI means to turn every one of the other types into a preset and a class per preset would have to follow each of those additions.

## State of UBI when this was written

This section records 2026-10-01. By 2026-10-02 UBI had built all four remaining joins and a preset for every fixed type; see the section on the 2026-10-02 audit below.

UBI merged stages one to three on 2026-10-01, as pull request #31 into its `main`: the order part with triggers, `protect` and pricing, the `then` and `either` joins, and thirteen presets (`simple`, `market_if_touched`, `limit_if_touched`, `scheduled`, `indicator_triggered`, `cross_instrument`, `hidden_stop`, `trailing_stop`, `trailing_entry`, `oto`, `oco`, `bracket`, `cover`). The joins `together`, `using`, `repeat` and `sequence` are reserved names that UBI refuses as not built yet, so they have no class here; each needs a class in `plan_parts` once UBI builds it.

Every plan built by the docstring examples was checked against UBI's own `PlanReader` from the branch before it was merged, and all of them were read without a problem, including the two preset combinations, where UBI turns `market_if_touched` plus `bracket` into a `then` join.

## The lower-case side bug in UBI, fixed on 2026-10-01

On 2026-10-01 the plan engine read the template's `transaction_type` straight from the stored body and compared it with `'BUY'` and `'SELL'`. This library sends `"buy"` and `"sell"`, which UBI stores as given, so for a plan sent from here a `price_crosses` trigger with no direction was read the wrong way round (a buy waited for a rise and fired at once), and a `protect` order failed, because `OPPOSITE_SIDES` only has upper-case keys. UBI's other types upper-case the side before using it. It is left for UBI to fix rather than worked around here, because upper-casing in `PlanOrder` alone would hide a bug that every other caller of UBI would still hit. Until UBI fixed it, every `PriceCrosses` needed an explicit `direction` and the `PlanOrder` example programs were not run.

UBI fixed it the same day in commit `220138a`, "Read a plan's side the way a validated order does", which strips and upper-cases the side in `PlanOrder._read_plan` and `OrderPart._opening_side` as a validated order does. Its live test on 2026-10-01 had confirmed the bug: three IDEA plans sent with `"buy"` fired on their first tick and were priced on the wrong side of the book. A lower-case side is safe from this library now, and no work-around is needed.

## The 2026-10-02 audit against UBI

On 2026-10-02 the plan parts were compared with UBI's `PlanReader` as it stood after about sixty commits that finished the plan. Every one of the fifteen part classes still built a document UBI accepted, so nothing here broke. What changed is that UBI's vocabulary grew far beyond these classes: the joins `together`, `sequence`, `repeat` and `using`; the `execution`, `guards`, `lifetime` and `venue` slots of an order; the pricings `peg`, `chase`, `follow_instrument`, `option_model`, `stages`, `from_fill` and `from_parent_fill`, with `cap` and `discretion` written beside a pricing in the same list; the triggers `time_from`, `candle_closes`, `account` and `limit_marketable`; the sides `close` and `against_delta`; quantity objects; and per-order overrides of the instrument, quantity, side, product, validity and tag. A part of a plan can now also be cancelled or changed on its own, by `parent_id` and its path in `part`, such as `root.each_fill.children.0` for a bracket's stop.

## UBI's plan fixes of 2026-10-05 (recorded 2026-10-06)

UBI's pull requests #69 to #73, merged on 2026-10-05, changed what a plan answers without changing what this library sends, so only docstrings changed here. The ones that matter to `PlanOrder` are these.

- A refused plan's problems are reported where the caller wrote them (commit `0ec2a34`). A value inside a preset that stands for a join, a repeat's copies or a using's pieces used to be reported at the part UBI built, such as `root.each_fill.children.0` for a bad stop price in a bracket preset, which the caller never wrote. The `path` is now the caller's, such as `root.presets.0`, and the running part is given as `part`. The message can still name the setting the preset becomes, such as `trigger_price` for a bracket's `stop_price`.
- A dry run makes the checks placing makes (commit `b507de0`), so a dry run of an exit with no position answers HTTP 409 with `protect_needs_position`, and one with a price off the tick answers HTTP 400, where both used to answer HTTP 200. In a dry run's `plan`, each order now shows `own_values`, its own side, and where its quantity comes from (commit `0ec2a34`); before, a basket's sell leg of another instrument read as the body's side.
- A parent can end `failed` after trading (commit `15380c1`), when an order meant to follow the trade, such as a hedge, a spread's second leg or a strategy stop's close, was refused, because a position may be left without it. A parent cancelled whole now ends `cancelled` with every part marked done (commit `8247bb7`), rather than leaving its parts `working` under a cancelled parent, and a fill arriving after that only records the update (commit `8c86310`).
- A done part's `reason` can also be `expired` (a lifetime or a pre-open ended it), `closed` (a lifetime's `close_filled` closed what it traded) or `nothing_held` (a close found nothing to close). These reasons predate the fixes, but UBI's documentation listed them for the first time.
- Cancelling one of a plan's broker orders by its `order_id` now takes that order's unfilled quantity off its part (commit `8247bb7`), so a later fill of the entry is protected for the new quantity only, and the cancelled order is not sent again. That is why the `cancel_part` docstring now contrasts the two ways of cancelling.
