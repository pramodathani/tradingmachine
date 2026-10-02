"""The parts a `PlanOrder` is built from, one class per part, each in its own module.

A plan describes an order as a tree rather than naming one of the fixed synthetic order types. Each class here builds one piece of the `plan` object UBI's order engine reads, through its `document()` method, and checks nothing itself, because UBI checks the whole plan and lists every problem it finds. An `OrderPart` takes the triggers, pricings, modifiers, executions, the guard, the lifetime, the venue and the quantities as its own arguments, and the joins take `OrderPart` objects and other joins as their children.

| Kind | Module | Class | UBI key |
|---|---|---|---|
| Node | `order_part` | `OrderPart` | `order` |
| Join | `then_part` | `ThenPart` | `then` |
| Join | `either_part` | `EitherPart` | `either` |
| Join | `together_part` | `TogetherPart` | `together` |
| Join | `sequence_part` | `SequencePart` | `sequence` |
| Join | `repeat_part` | `RepeatPart` | `repeat` |
| Join | `using_part` | `UsingPart` | `using` |
| Preset | `preset` | `Preset` | any preset name, such as `bracket` |
| Trigger | `price_crosses` | `PriceCrosses` | `price_crosses` |
| Trigger | `trails` | `Trails` | `trails` |
| Trigger | `candle_closes` | `CandleCloses` | `candle_closes` |
| Trigger | `account_condition` | `AccountCondition` | `account` |
| Trigger | `limit_marketable` | `LimitMarketable` | `limit_marketable` |
| Trigger | `time_at` | `TimeAt` | `time_at` |
| Trigger | `time_after` | `TimeAfter` | `time_after` |
| Trigger | `time_before` | `TimeBefore` | `time_before` |
| Trigger | `time_from` | `TimeFrom` | `time_from` |
| Trigger | `all_conditions` | `AllConditions` | `all` |
| Trigger | `any_condition` | `AnyCondition` | `any` |
| Pricing | `fixed_pricing` | `FixedPricing` | `fixed` |
| Pricing | `marketable_pricing` | `MarketablePricing` | `marketable` |
| Pricing | `native_stop_pricing` | `NativeStopPricing` | `native_stop` |
| Pricing | `trail_pricing` | `TrailPricing` | `trail` |
| Pricing | `peg_pricing` | `PegPricing` | `peg` |
| Pricing | `chase_pricing` | `ChasePricing` | `chase` |
| Pricing | `follow_instrument_pricing` | `FollowInstrumentPricing` | `follow_instrument` |
| Pricing | `option_model_pricing` | `OptionModelPricing` | `option_model` |
| Pricing | `stages_pricing` | `StagesPricing` | `stages` |
| Pricing | `stage_rule` | `StageRule` | one entry of `stages` `rules` |
| Pricing | `from_fill_pricing` | `FromFillPricing` | `from_fill` |
| Pricing | `from_parent_fill_pricing` | `FromParentFillPricing` | `from_parent_fill` |
| Pricing modifier | `cap_modifier` | `CapModifier` | `cap` |
| Pricing modifier | `discretion_modifier` | `DiscretionModifier` | `discretion` |
| Execution | `all_at_once_execution` | `AllAtOnceExecution` | `all_at_once` |
| Execution | `iceberg_execution` | `IcebergExecution` | `iceberg` |
| Execution | `twap_execution` | `TwapExecution` | `twap` |
| Execution | `vwap_execution` | `VwapExecution` | `vwap` |
| Execution | `front_loaded_execution` | `FrontLoadedExecution` | `front_loaded` |
| Execution | `participation_execution` | `ParticipationExecution` | `participation` |
| Execution | `book_depth_execution` | `BookDepthExecution` | `book_depth` |
| Execution | `top_up_execution` | `TopUpExecution` | `top_up` |
| Execution | `daily_execution` | `DailyExecution` | `daily` |
| Execution | `ladder_execution` | `LadderExecution` | `ladder` |
| Execution | `freeze_limit_execution` | `FreezeLimitExecution` | `freeze_limit` |
| Guard | `post_only_guard` | `PostOnlyGuard` | `post_only` |
| Lifetime | `lifetime` | `Lifetime` | one entry of `lifetime` |
| Venue | `pre_open_venue` | `PreOpenVenue` | one entry of `venue`, `pre_open` |
| Venue | `paper_venue` | `PaperVenue` | one entry of `venue`, `paper` |
| Quantity | `position_quantity` | `PositionQuantity` | `position` |
| Quantity | `parent_fill_quantity` | `ParentFillQuantity` | `parent_fill` |
| Quantity | `parent_fill_delta_quantity` | `ParentFillDeltaQuantity` | `parent_fill_delta` |

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
