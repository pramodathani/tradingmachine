# src/tradingmachine/orders/virtual_limit.py

`VirtualLimitOrder` mirrors UBI's `virtual_limit` synthetic order type, `unified_broker_interface/utilities/order_engine/virtual_limit.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

It is not an Atlas row; UBI added it on 2026-09-24 with its `virtual_book` queue estimate. `paper` is sent only when True, because UBI counts only a literal true and False says nothing UBI does not assume.
