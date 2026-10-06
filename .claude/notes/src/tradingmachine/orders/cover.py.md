# src/tradingmachine/orders/cover.py

`CoverOrder` mirrors UBI's `cover` synthetic order type, `unified_broker_interface/utilities/order_engine/cover.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row D6 cover order.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

The stop is required and a target is refused with HTTP 400 rather than ignored, which is the whole difference from a bracket without a target. The class therefore has no `target_price` parameter at all.

## UBI's fixes of 2026-10-05, recorded on 2026-10-06

UBI's commit `15380c1` made a refused order in a Then join's child cancel the rest of the first plan and end the parent `failed` rather than `completed`, which applies to a cover order's stop, so the docstrings now say so.
