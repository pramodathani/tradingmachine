"""UBI's synthetic order types, one class per type, each in its own module.

A synthetic order is an order no Indian exchange offers, built by UBI's order engine out of ordinary broker orders: a bracket, a trailing stop, an iceberg, a time-sliced order and so on. Each class takes an instrument and an order template, the ordinary order fields, plus its own settings, and `place()` sends it through `TradeableInstrument.place_order`. They need UBI to run in engine mode, and `place_order` refuses to send them otherwise. Several of them place, change or cancel real orders long after `place()` has returned, so send `dry_run=True` first.

The module names spell out the abbreviations UBI uses for the type names:

| UBI type | Module | Class |
|---|---|---|
| `simple` | `simple` | `SimpleOrder` |
| `freeze_slicer` | `freeze_slicer` | `FreezeSlicerOrder` |
| `ladder` | `ladder` | `LadderOrder` |
| `grid` | `grid` | `GridOrder` |
| `oto` | `one_triggers_other` | `OneTriggersOtherOrder` |
| `oco` | `one_cancels_other` | `OneCancelsOtherOrder` |
| `bracket` | `bracket` | `BracketOrder` |
| `cover` | `cover` | `CoverOrder` |
| `scale_out` | `scale_out` | `ScaleOutOrder` |
| `two_sided_breakout` | `two_sided_breakout` | `TwoSidedBreakoutOrder` |
| `scheduled` | `scheduled` | `ScheduledOrder` |
| `good_till_time` | `good_till_time` | `GoodTillTimeOrder` |
| `time_stop` | `time_stop` | `TimeStopOrder` |
| `square_off` | `square_off` | `SquareOffOrder` |
| `twap` | `time_weighted_average_price` | `TimeWeightedAveragePriceOrder` |
| `vwap` | `volume_weighted_average_price` | `VolumeWeightedAveragePriceOrder` |
| `implementation_shortfall` | `implementation_shortfall` | `ImplementationShortfallOrder` |
| `participation` | `participation` | `ParticipationOrder` |
| `liquidity_seeking` | `liquidity_seeking` | `LiquiditySeekingOrder` |
| `iceberg` | `iceberg` | `IcebergOrder` |
| `accumulation` | `accumulation` | `AccumulationOrder` |
| `peg` | `peg` | `PegOrder` |
| `chaser` | `chaser` | `ChaserOrder` |
| `post_only` | `post_only` | `PostOnlyOrder` |
| `discretionary` | `discretionary` | `DiscretionaryOrder` |
| `virtual_limit` | `virtual_limit` | `VirtualLimitOrder` |
| `market_if_touched` | `market_if_touched` | `MarketIfTouchedOrder` |
| `limit_if_touched` | `limit_if_touched` | `LimitIfTouchedOrder` |
| `cross_instrument` | `cross_instrument` | `CrossInstrumentOrder` |
| `indicator_triggered` | `indicator_triggered` | `IndicatorTriggeredOrder` |
| `gtt` | `good_till_triggered` | `GoodTillTriggeredOrder` |
| `hidden_stop` | `hidden_stop` | `HiddenStopOrder` |
| `candle_close_stop` | `candle_close_stop` | `CandleCloseStopOrder` |
| `trailing_stop` | `trailing_stop` | `TrailingStopOrder` |
| `trailing_entry` | `trailing_entry` | `TrailingEntryOrder` |
| `atr_trail` | `average_true_range_trail` | `AverageTrueRangeTrailOrder` |
| `daily_stop` | `daily_stop` | `DailyStopOrder` |
| `basket` | `basket` | `BasketOrder` |
| `oca` | `one_cancels_all` | `OneCancelsAllOrder` |
| `legged_spread` | `legged_spread` | `LeggedSpreadOrder` |
| `strategy_stop` | `strategy_stop` | `StrategyStopOrder` |
| `exposure_hedge` | `exposure_hedge` | `ExposureHedgeOrder` |

`synthetic_order` holds the shared base, `SyntheticOrder`, and `order_candidate` and `exposure_watch` hold the two small classes the multi-instrument types take as arguments.

Nothing is imported here, so import the module you need.

Typical usage example:

  from tradingmachine.orders import bracket

  order = bracket.BracketOrder(
      share,
      transaction_type="buy",
      product="mis",
      order_type="limit",
      quantity=10,
      price=1000.0,
      stop_price=990.0,
      stop_limit_price=988.0,
      target_price=1010.0,
      dry_run=True,
  )
  answer = order.place()
"""
