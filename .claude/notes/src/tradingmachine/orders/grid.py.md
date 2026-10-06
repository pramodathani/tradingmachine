# src/tradingmachine/orders/grid.py

`GridOrder` mirrors UBI's `grid` synthetic order type, `unified_broker_interface/utilities/order_engine/grid.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row E4 grid, and G15 scale order with profit-taker.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

`most_inventory` is required by UBI rather than defaulted, because a trending market keeps filling one side and a grid with no cap would build an unlimited position. The class keeps it required for the same reason. The Atlas's G15, a ladder where each fill gets its own profit-taker, is the same mechanism, which is why the gap analysis on 2026-09-26 counted it as covered.

## UBI's fixes of 2026-10-05, recorded on 2026-10-06

UBI's commit `d3a354c` began refusing a `step_points` that is not a whole number of ticks with HTTP 400. Before, the order answering a filled rung was priced one step away without rounding, so a step of 2.53 gave a sell at 1000.03 that the placement refused after the fill had already been marked answered, leaving the position with no exit. UBI's commit `8c86310` stopped a parent that has ended from settling its plan again, because a fill arriving after the caller cancelled a grid used to place a new order that then rested at the broker under a cancelled parent. The docstrings were brought in line with both on 2026-10-06, together with UBI's clarification that the inventory cap is checked after each fill and can therefore be overshot by one fill.
