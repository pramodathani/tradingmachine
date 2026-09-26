# src/tradingmachine/orders/simple.py

`SimpleOrder` mirrors UBI's `simple` synthetic order type, `unified_broker_interface/utilities/order_engine/simple.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

It is not an Atlas row: it is the plain order UBI's engine runs when no `synthetic` object is sent. It exists as a named class so that a plain order can be marked `closes_position`, which is how `TradeableInstrument.reduce_position` and `liquidate_position` use it through `place_order`.
