# src/tradingmachine/orders/trailing_stop.py

`TrailingStopOrder` mirrors UBI's `trailing_stop` synthetic order type, `unified_broker_interface/utilities/order_engine/trailing_stop.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row B7 trailing stop.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI keeps a real stop-limit at the broker and moves its trigger, the Atlas's resting build, so the stop keeps protecting the position while UBI is down. `trail_points` and `trail_percent` are both optional here and UBI requires exactly one.
