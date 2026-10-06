# src/tradingmachine/orders/bracket.py

`BracketOrder` mirrors UBI's `bracket` synthetic order type, `unified_broker_interface/utilities/order_engine/bracket.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row D5 bracket order.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

The exits are armed on the first partial fill and sized to what filled, which UBI's notes describe as the difference between a bracket that protects a position and one that protects a position it expects to have. Every stop is a stop-limit, so `stop_limit_price` is required whenever `stop_price` is given, and UBI refuses rather than defaults it.

## UBI's fixes of 2026-10-05, recorded on 2026-10-06

UBI's commit `8247bb7` changed what happens to an exit that has finished. A rule of 2026-10-04 reopened any exit done as cancelled, so a bracket's stop cancelled by its `order_id` was placed again as soon as the cancel was confirmed, and every exchange cancel of a target placed another until one was rejected. A finished exit is now reopened only once its target grows past the target it had when it finished, and a caller's cancel by `order_id` takes the order's unfilled quantity off its part. UBI's commit `15380c1` made a refused exit cancel the rest of the entry and end the parent `failed`, and its commit `b507de0` made a dry run make the off-tick checks placing makes. The docstrings now describe all three.
