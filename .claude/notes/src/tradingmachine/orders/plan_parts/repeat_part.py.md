# src/tradingmachine/orders/plan_parts/repeat_part.py

`RepeatPart` mirrors UBI's `RepeatPart`, in `unified_broker_interface/utilities/order_engine/utilities/repeat_part.py` in the sibling project, read by `PlanReader._read_repeat` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`. UBI's `accumulation` preset expands to this join.

## The JSON shape

```json
{"repeat": {"child": {"order": {}}, "times": 6, "every_minutes": 30, "until": {"price_crosses": {"level": 1050.0, "direction": "at_or_above"}}}}
```

| Key | Rule |
|---|---|
| `child` | Required, and must be an order node, `{"order": {...}}`; a join is refused as `repeat_needs_order` |
| `times` | Required, a whole number from 1 to 100 (`MOST_REPEATS`) |
| `every_minutes` | A number above zero; the first copy goes at once and copy `n` waits `n * every_minutes` from when the plan was placed |
| `every_trading_day_at` | A time of day such as `09:20`; each copy goes at that time on its own trading day, weekends and holidays skipped, and the plan is kept across days |
| `until` | A condition, read by `_read_condition`, not a plan node |

Exactly one of `every_minutes` and `every_trading_day_at` must be given; both or neither is refused as `bad_setting`. The class leaves both optional and sends whichever is set, following the rule that UBI checks the plan rather than this library.

## Rules that bite

- `until` ends every copy still waiting by giving it a lifetime, so the child must not carry a `Lifetime` of its own (`until_with_lifetime`). Copies already sent are left as they are.
- A copy with a trigger of its own waits for both its trigger and its turn, because UBI joins the two with `all`.
- A copy that does not fill is left resting.
- A repeat join cannot be a `then` join's child (`join_not_sized`).

`until` is typed as a `PlanPart` because conditions are `PlanPart` objects in this library, but only a condition, such as `PriceCrosses`, `TimeAt` or `AccountCondition`, is accepted by UBI there.
