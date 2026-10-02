# src/tradingmachine/orders/plan_parts/peg_pricing.py

`PegPricing` mirrors UBI's `PegPricing`, in `unified_broker_interface/utilities/order_engine/utilities/peg_pricing.py` in the sibling project, which `PlanReader._read_peg` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` builds. It was written on 2026-10-02.

## The JSON shape

```json
{"peg": {"reference": "mid", "offset_ticks": 1, "follows": false, "within_body_price": true}}
```

Every key is optional, and an empty `{"peg": {}}` is a valid peg to the own touch. The defaults are `reference` `own_touch`, `offset_ticks` 0, `follows` true and `within_body_price` false. `reference` must be one of UBI's `REFERENCES`, `own_touch`, `mid` or `opposite_touch`; `offset_ticks` must be a whole number, and a bool is refused; any other key is refused with `unknown_setting`.

## Why the booleans are typed differently

`follows` defaults to true in UBI, so the class takes `bool | None = None` and sends it only when it is not None, which is the only way to say false. `within_body_price` defaults to false, so the class takes `bool = False` and sends it only when True. This is the spec's general rule for booleans.

## Rules that bite

- A peg to `opposite_touch` means to trade at once, so `PlanReader._can_rest` refuses it beside a `PostOnlyGuard` with `post_only_crosses`. A peg to `own_touch` or `mid` may carry the guard.
- `within_body_price` reads the *template's* limit price, the `price` of the `PlanOrder`, not a `FixedPricing` in the same order, because an order holds only one pricing setter and a second is refused with `two_setters`. The example `one_shot_bid_within_a_limit.py` therefore builds a `PlanOrder` (without placing it) so the template's price is real.
- `follows: false` with `within_body_price` is how UBI's `accumulation` preset prices each purchase.
- A pegged order may sit inside a `TwapExecution` and similar executions, and UBI moves every piece still resting.
