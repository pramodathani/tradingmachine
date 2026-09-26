# src/tradingmachine/orders/scale_out.py

`ScaleOutOrder` mirrors UBI's `scale_out` synthetic order type, `unified_broker_interface/utilities/order_engine/scale_out.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row D7 multi-target bracket or scale-out, and part of G8 adjustable stop.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

`target_prices` is copied into a new list so that a caller changing their own list afterwards does not change the order. `breakeven_after` is the one piece of the Atlas's G8 adjustable stop that UBI has built; the general rule table is not built.
