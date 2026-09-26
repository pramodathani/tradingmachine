# src/tradingmachine/orders/post_only.py

`PostOnlyOrder` mirrors UBI's `post_only` synthetic order type, `unified_broker_interface/utilities/order_engine/post_only.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row A5 post-only.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

The Atlas lists true post-only among the things that cannot be guaranteed, because the book can move while the order is in flight. UBI's default, `refuse`, answers HTTP 409, which is raised as `ConflictError`.
