# src/tradingmachine/orders/time_stop.py

`TimeStopOrder` mirrors UBI's `time_stop` synthetic order type, `unified_broker_interface/utilities/order_engine/time_stop.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row C3 time stop.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

`until_time` and `minutes` are both optional here and UBI requires exactly one; the class does not check that, because UBI answers HTTP 400 naming the fields.
