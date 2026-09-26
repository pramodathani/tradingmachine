# src/tradingmachine/orders/limit_if_touched.py

`LimitIfTouchedOrder` mirrors UBI's `limit_if_touched` synthetic order type, `unified_broker_interface/utilities/order_engine/limit_if_touched.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row B6 limit-if-touched.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

`trigger_price` is the touch level and is stored as `trigger_level`, for the reason given in the note on `market_if_touched.py`. `limit_price` is required because UBI deliberately does not default it to the trigger.
