# src/tradingmachine/orders/trailing_entry.py

`TrailingEntryOrder` mirrors UBI's `trailing_entry` synthetic order type, `unified_broker_interface/utilities/order_engine/trailing_entry.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row B9 trailing entry.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

It shares UBI's trailing mechanism with `trailing_stop`, in `utilities/trailing.py`, and takes the same fields.
