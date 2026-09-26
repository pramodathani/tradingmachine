# Synthetic orders

!!! danger "These place real orders, sometimes long after you ask"

    A synthetic order can place, change or cancel orders at a broker minutes, hours or days after
    `place()` returns, with nobody watching: a trigger fires when the price arrives, a scheduled
    order goes out at its time, a bracket places its exits as the entry fills. Send
    `dry_run=True` first, which has UBI build the first broker request without recording or sending
    anything.

A synthetic order is an order no Indian exchange offers, built by UBI's order engine out of the four
orders an exchange does accept: market, limit, stop-loss limit and stop-loss market. You describe the
whole idea once, such as "buy here, protect it with a stop and a target", and UBI's engine places the
real orders, watches their fills and changes what is resting as things happen.

`tradingmachine.orders` has one class for each of the forty-two types UBI runs, each in its own
module. The classes only describe an order and send it; everything else happens inside UBI.

## Sending one

Every class takes an instrument, the ordinary order fields that make up the **template**, and its
own settings, all by keyword. `place()` sends it through `TradeableInstrument.place_order`.

```python
from tradingmachine.assets import equities
from tradingmachine.orders import bracket

share = equities.Equity(exchange="nse", symbol="RELIANCE")

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
```

The template is validated exactly as a plain order is, and most types use it for every real order
they send, changing only what they must. The type's own settings are UBI's field names, and nothing
is checked before sending: UBI's engine checks each field and answers HTTP 400 naming the one that
is wrong, which a dry run shows without sending anything.

!!! warning "Engine mode only"

    Synthetic orders need UBI to run its order engine. In direct mode UBI would place the template
    as one plain order and ignore the rest, so a bracket would go out with no stop. `place_order`
    checks first and raises `DirectPlacementError` without sending anything when the engine is not
    there. See [Orders](orders.md).

## What comes back

A type that acts at once answers with the broker's answer plus a `parent_id`, and `freeze_slicer`
and `ladder` add a list of `order_ids`, one per order they placed. A type that waits for a price or a
time answers HTTP 202, which is not an error:

```python
{
    "broker": None,
    "order_id": None,
    "outcome": "armed",
    "parent_id": "...",
    "status_message": "the order is recorded and will be placed when the price touches the level",
}
```

Keep the `parent_id`. Until the order reaches a broker it is the only handle on it, and UBI has no
route to list or cancel one yet; see [Known issues](../contributing/known-issues.md).

## The forty-two types

The table below groups the types by what each one waits for. The module names spell out UBI's
abbreviations, so UBI's `oto` is `one_triggers_other` and its `atr_trail` is
`average_true_range_trail`.

| Family | Classes | What they do |
| --- | --- | --- |
| Plain and laddered | `SimpleOrder`, `FreezeSlicerOrder`, `LadderOrder`, `GridOrder` | Send their orders at once: one order, an order split under the freeze quantity, a ladder of limits, or a grid that re-places each fill's opposite |
| Linked | `OneTriggersOtherOrder`, `OneCancelsOtherOrder`, `BracketOrder`, `CoverOrder`, `ScaleOutOrder`, `TwoSidedBreakoutOrder` | Act on fills: a second order after the first fills, a stop and a target that shrink together, an entry that arms its own exits |
| Time-based | `ScheduledOrder`, `GoodTillTimeOrder`, `TimeStopOrder`, `SquareOffOrder` | Act at a time of day: place later, cancel later, close later, or square off the day's positions yourself |
| Execution algorithms | `TimeWeightedAveragePriceOrder`, `VolumeWeightedAveragePriceOrder`, `ImplementationShortfallOrder`, `ParticipationOrder`, `LiquiditySeekingOrder`, `IcebergOrder`, `AccumulationOrder` | Work a large order over time or against the market's volume |
| Book-following | `PegOrder`, `ChaserOrder`, `PostOnlyOrder`, `DiscretionaryOrder`, `VirtualLimitOrder` | Price a limit order against the live book and keep re-pricing it |
| Price triggers | `MarketIfTouchedOrder`, `LimitIfTouchedOrder`, `CrossInstrumentOrder`, `IndicatorTriggeredOrder`, `GoodTillTriggeredOrder` | Wait unseen for a price, then send one order |
| Stops and trailing | `HiddenStopOrder`, `CandleCloseStopOrder`, `TrailingStopOrder`, `TrailingEntryOrder`, `AverageTrueRangeTrailOrder`, `DailyStopOrder` | Protect a position or enter on a move |
| Several instruments | `BasketOrder`, `OneCancelsAllOrder`, `LeggedSpreadOrder`, `StrategyStopOrder`, `ExposureHedgeOrder` | Place or watch orders on more than one instrument |

Each class's docstring gives its settings, their defaults and their limits, and the
[API reference](../reference/tradingmachine/orders/index.md) lists them all.

## Four things that are easy to get wrong

**Every stop is a stop-limit.** Stop-loss market orders are gone for NSE options and all of BSE, so
wherever a type places a stop you give both its trigger and its limit, and UBI does not default the
limit. A limit equal to the trigger will often not fill, because the price runs straight through it.

**In a trigger type, `trigger_price` is the level, not the order's trigger.** For
`MarketIfTouchedOrder`, `LimitIfTouchedOrder`, `CrossInstrumentOrder`, `IndicatorTriggeredOrder`,
`GoodTillTriggeredOrder`, `HiddenStopOrder` and `CandleCloseStopOrder`, `trigger_price` is the price
that fires the order. These classes store it as `trigger_level` and take no order trigger, because
the order they fire is a limit.

**Protecting a position means naming the side that opened it.** For `OneCancelsOtherOrder`,
`HiddenStopOrder` and the other types that protect a position, `transaction_type` is the side of the
position, not of the exit. A long position is protected by asking for `buy`, and the exits are sells.

**The template leaks into every leg.** UBI builds each candidate of a multi-instrument order, and the
second order of a `OneTriggersOtherOrder`, by laying its own fields over the whole template. A
template `price` is therefore carried into a leg that sets `order_type="market"`, and UBI refuses a
market order that carries a price. Give such a template no price, or give each leg its own.

## Several instruments

`BasketOrder`, `OneCancelsAllOrder`, `StrategyStopOrder` and `LeggedSpreadOrder` take
`OrderCandidate` objects, one per instrument, each overriding whichever template fields it needs.

```python
from tradingmachine.orders import basket
from tradingmachine.orders import order_candidate

order = basket.BasketOrder(
    candidates=[
        order_candidate.OrderCandidate(reliance, price=1450.0),
        order_candidate.OrderCandidate(infosys, price=1500.0),
    ],
    transaction_type="buy",
    product="cnc",
    order_type="limit",
    quantity=1,
    dry_run=True,
)
```

The first candidate's instrument anchors the request, because UBI checks the template before its
engine places only the candidates. A dry run of a basket prepares only that first candidate.
`ExposureHedgeOrder` takes `ExposureWatch` objects instead, one per watched instrument, with an
`exposure_per_unit` that is where an option's delta goes, since UBI has no option pricing model.

## Order types that need no class

UBI's order engine was designed from a survey of order types called the Synthetic Order Atlas, and
eight of the types it covers need no class, because they are a field on an ordinary order, a route
of their own, or something the exchange already does.

| Atlas type | How to ask for it here |
| --- | --- |
| Marketable limit | `buy_at_marketable_price` and `sell_at_marketable_price` |
| Market-to-limit | `buy_at_best_offer_price` and `sell_at_best_bid_price` |
| Immediate-or-cancel | `validity="ioc"` on any order |
| Stop-market | `place_order` with `order_type="sl"` and a limit set well past the trigger |
| Stop entry (breakout) | `place_order` with `order_type="sl"`, a buy stop above the price or a sell stop below it |
| One-updates-other | Nothing to ask for: every linked type reduces the other leg rather than cancelling it |
| Kill switch | `Account.flatten`; see [The account](account.md) |
| Daily loss lockout | A limit set in UBI's configuration; an order refused by it raises `LossLockoutError` |

The Atlas's last group, seventeen further types from brokers' own catalogues, is mostly not built in
UBI yet, and [Known issues](../contributing/known-issues.md) lists what is missing.
