# src/tradingmachine/orders/plan_parts/paper_venue.py

`PaperVenue` mirrors UBI's `PaperVenue`, in `unified_broker_interface/utilities/order_engine/utilities/paper_venue.py` in the sibling project, read by `PlanReader._read_venue_list` and checked by `PlanReader._can_fill_on_paper` in `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py`. The `virtual_limit` preset with `paper: true` builds it.

## The JSON shape

```json
{"order": {"trigger": {"limit_marketable": {}}, "venue": [{"session": "paper"}]}}
```

The entry takes `session` alone; any other key is refused. It has no settings, so the class has no constructor and no `Attributes:` section.

## Rules that bite

- The order's trigger must be `limit_marketable` alone (`paper_needs_limit_marketable`); a group of conditions is refused even if it contains one.
- Because of that trigger, the order takes no pricing of its own and is held at the body's own `LIMIT` price (`held_at_the_body_price`).
- The order must be the whole plan, at path `root` (`paper_is_the_whole_plan`), so it cannot sit in any join.
- Nothing reaches a broker. Fills come from the virtual book's queue estimate and are recorded as `paper_filled` events, and the plan completes once the whole quantity has filled.

## Paper fills take what the book offers, since 2026-10-07

UBI's commit `a6b2169` of 2026-10-07 changed how a paper order fills. Before it, a paper limit filled its whole remaining quantity at its limit price the moment the other side of the book reached that price, however little was offered there. Now `PaperVenue` in UBI walks the other side's levels at or better than the limit once, at that moment, and fills what they hold at their own prices, storing the walk as `paper_touch` so the same liquidity is never taken twice and a restart does not walk again; the rest keeps filling from the queue estimate at the limit. Each `paper_filled` event now carries `average_price`, the average of everything filled so far. The docstring was brought up to date on 2026-10-31; nothing this library sends changed.
