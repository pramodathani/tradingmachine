# src/tradingmachine/orders/virtual_limit.py

`VirtualLimitOrder` mirrors UBI's `virtual_limit` synthetic order type, `unified_broker_interface/utilities/order_engine/virtual_limit.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

It is not an Atlas row; UBI added it on 2026-09-24 with its `virtual_book` queue estimate. `paper` is sent only when True, because UBI counts only a literal true and False says nothing UBI does not assume.

Since 2026-09-27 UBI holds every plain limit order with a price, `day` validity and no `synthetic` object as a `virtual_limit` by default, controlled by `UNIFIED_BROKER_INTERFACE_API_ORDER_HOLD_LIMITS` on the UBI side. The class is kept for `paper` and to ask for the type explicitly.

## Paper fills take what the book offers, since 2026-10-07

UBI's commit `a6b2169` of 2026-10-07 changed how a paper order fills. Before it, a paper limit filled its whole remaining quantity at its limit price the moment the other side of the book reached that price, however little was offered there. Now `PaperVenue` in UBI walks the other side's levels at or better than the limit once, at that moment, and fills what they hold at their own prices, storing the walk as `paper_touch` so the same liquidity is never taken twice and a restart does not walk again; the rest keeps filling from the queue estimate at the limit. Each `paper_filled` event now carries `average_price`, the average of everything filled so far. The docstring was brought up to date on 2026-10-31; nothing this library sends changed.
