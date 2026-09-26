# src/tradingmachine/orders/indicator_triggered.py

`IndicatorTriggeredOrder` mirrors UBI's `indicator_triggered` synthetic order type, `unified_broker_interface/utilities/order_engine/indicator_triggered.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row B11 indicator-triggered, and part of G10.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

It compares one field of the live quote, not a computed indicator. With `watch_field` set to `best_bid` or `best_offer` it is also part of the Atlas's G10, stops triggered by something other than the last price. `trigger_price` is stored as `trigger_level`.
