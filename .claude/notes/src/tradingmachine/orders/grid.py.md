# src/tradingmachine/orders/grid.py

`GridOrder` mirrors UBI's `grid` synthetic order type, `unified_broker_interface/utilities/order_engine/grid.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row E4 grid, and G15 scale order with profit-taker.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

`most_inventory` is required by UBI rather than defaulted, because a trending market keeps filling one side and a grid with no cap would build an unlimited position. The class keeps it required for the same reason. The Atlas's G15, a ladder where each fill gets its own profit-taker, is the same mechanism, which is why the gap analysis on 2026-09-26 counted it as covered.
