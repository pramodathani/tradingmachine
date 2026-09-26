# src/tradingmachine/orders/time_weighted_average_price.py

`TimeWeightedAveragePriceOrder` mirrors UBI's `twap` synthetic order type, `unified_broker_interface/utilities/order_engine/twap.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row E5 TWAP.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

The module name spells out `twap`, following the user's rule against abbreviations.
