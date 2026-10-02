# src/tradingmachine/orders/plan_parts/limit_marketable.py

`LimitMarketable` mirrors UBI's `LimitMarketableCondition`, in `unified_broker_interface/utilities/order_engine/utilities/limit_marketable_condition.py` in the sibling project, read inline by `PlanReader._read_condition` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`. It keeps the rules of the `virtual_limit` synthetic type, whose preset builds this condition, and with `paper: true` adds the paper venue.

The class takes no arguments and has no `__init__`, because the condition has no settings.

## The JSON shape

```json
{"limit_marketable": {}}
```

Anything other than an empty object is refused with `bad_setting`.

## Rules that bite

- **The order takes no pricing of its own.** `PlanReader._holds_at_its_limit` looks for the condition on its own or anywhere inside an `all` or `any` group, and when it is there `_held_at_the_body_price` accepts only the default pricing, a `fixed` setter with neither a price nor an order type. Any pricing rule, even `FixedPricing(price=...)`, is refused with `held_at_the_body_price`. The price is the plan's template's own `LIMIT` price.
- **The template must be a LIMIT order with a price.** That is checked when the plan is placed, not by the offline reader, and refused with HTTP 400. The examples therefore print only the order part and say in words what the template carries.
- It holds once the opposite touch reaches the limit: for a buy, the best offer at or below it, and for a sell, the best bid at or above it. A stale quote never holds.
- When the plan is placed, the condition writes the held terms into its memory, and `bin/unified/orders/virtual_book` estimates from them how much a resting order at the same limit would have filled. When the order is sent, that estimate is kept as `missed_quantity` in the part's record.
- A `PaperVenue` order must wait on `limit_marketable` alone and be the whole plan, because its fills come from that estimate.
