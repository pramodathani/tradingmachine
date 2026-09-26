# src/tradingmachine/orders/average_true_range_trail.py

`AverageTrueRangeTrailOrder` mirrors UBI's `atr_trail` synthetic order type, `unified_broker_interface/utilities/order_engine/atr_trail.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row B8 ATR or indicator trail.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

The module name and the `average_true_range_multiple` parameter spell out UBI's `atr_trail` and `atr_multiple`; `synthetic_fields()` sends the parameter under UBI's name.
