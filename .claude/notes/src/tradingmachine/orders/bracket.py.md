# src/tradingmachine/orders/bracket.py

`BracketOrder` mirrors UBI's `bracket` synthetic order type, `unified_broker_interface/utilities/order_engine/bracket.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row D5 bracket order.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

The exits are armed on the first partial fill and sized to what filled, which UBI's notes describe as the difference between a bracket that protects a position and one that protects a position it expects to have. Every stop is a stop-limit, so `stop_limit_price` is required whenever `stop_price` is given, and UBI refuses rather than defaults it.
