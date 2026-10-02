"""The parts a `PlanOrder` is built from, one class per part, each in its own module.

A plan describes an order as a tree rather than naming one of the fixed synthetic order types. Each class here builds one piece of the `plan` object UBI's order engine reads, through its `document()` method, and checks nothing itself, because UBI checks the whole plan and lists every problem it finds.

| Kind | Module | Class | UBI key |
|---|---|---|---|
| Node | `order_part` | `OrderPart` | `order` |
| Node | `then_part` | `ThenPart` | `then` |
| Node | `either_part` | `EitherPart` | `either` |
| Preset | `preset` | `Preset` | any preset name, such as `bracket` |
| Trigger | `price_crosses` | `PriceCrosses` | `price_crosses` |
| Trigger | `trails` | `Trails` | `trails` |
| Trigger | `time_at` | `TimeAt` | `time_at` |
| Trigger | `time_after` | `TimeAfter` | `time_after` |
| Trigger | `time_before` | `TimeBefore` | `time_before` |
| Trigger | `all_conditions` | `AllConditions` | `all` |
| Trigger | `any_condition` | `AnyCondition` | `any` |
| Pricing | `fixed_pricing` | `FixedPricing` | `fixed` |
| Pricing | `marketable_pricing` | `MarketablePricing` | `marketable` |
| Pricing | `native_stop_pricing` | `NativeStopPricing` | `native_stop` |
| Pricing | `trail_pricing` | `TrailPricing` | `trail` |

`plan_part` holds the shared base, `PlanPart`.

Nothing is imported here, so import the module you need.

Typical usage example:

  from tradingmachine.orders.plan_parts import order_part
  from tradingmachine.orders.plan_parts import price_crosses
  from tradingmachine.orders.plan_parts import then_part
  from tradingmachine.orders.plan_parts import trail_pricing

  plan = then_part.ThenPart(
      first=order_part.OrderPart(
          trigger=price_crosses.PriceCrosses(level=995.0),
      ),
      each_fill=order_part.OrderPart(
          side="protect",
          pricing=trail_pricing.TrailPricing(points=5.0, limit_offset=1.0),
      ),
  )
  document = plan.document()
"""
