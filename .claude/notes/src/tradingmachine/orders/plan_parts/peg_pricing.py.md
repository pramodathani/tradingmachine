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

## on_empty_book, added on 2026-10-06

UBI's commit `165a2ad` gave the peg the setting `on_empty_book`, `wait` by default or `refuse`. With `refuse`, a peg that cannot be priced when it is first sent, because nobody is on the side its reference reads, no live quote has arrived or the quote is marked stale, ends its part as refused, and a plan with nothing else placed answers HTTP 409. UBI built it for its `marketable_limit` preset. The attribute is sent only when it is not None, like `reference` and `follows`, and its value is not checked here because UBI refuses any other value with HTTP 400.

## maximum_cost_bps and reaches_size, added on 2026-10-31

UBI's commits `63e3d68` and `102da2e` of 2026-10-07 gave the peg two more settings, which `PlanReader._read_peg` accepts beside the others. `maximum_cost_bps` must be a number above zero and is absent by default; with it, the peg's order is refused just before it is sent, as `on_empty_book: refuse` refuses it, when the pre-trade estimate of filling the whole quantity against the visible book is above that many basis points of the midpoint or the book cannot hold the quantity. `reaches_size` defaults to false and is refused with `bad_setting` unless the reference is `opposite_touch`, because only the other side of the book holds what the order would take.

UBI's two switches, `UNIFIED_BROKER_INTERFACE_API_ORDER_MAXIMUM_COST_BPS` and `UNIFIED_BROKER_INTERFACE_API_ORDER_MARKET_REACHES_SIZE`, are applied by `PlanRouting` only to the `marketable_limit` type, never to a peg written by hand in a plan. So the general rule for booleans applies here: `reaches_size` takes `bool = False` and is sent only when True, and `maximum_cost_bps` takes `float | None = None` and is sent only when set. This differs on purpose from `MarketableLimitOrder.reaches_size`, which is `bool | None` because a switch stands behind it.
