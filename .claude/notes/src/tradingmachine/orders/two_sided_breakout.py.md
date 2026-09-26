# src/tradingmachine/orders/two_sided_breakout.py

`TwoSidedBreakoutOrder` mirrors UBI's `two_sided_breakout` synthetic order type, `unified_broker_interface/utilities/order_engine/two_sided_breakout.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row D8 two-sided breakout.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

Both entries are native stops, so the template usually has `order_type` `sl`; UBI builds the two entries from `buy_trigger`, `buy_limit`, `sell_trigger` and `sell_limit`. UBI never resolves references for this type. The optional exits are armed after the break exactly as for `oco`.
