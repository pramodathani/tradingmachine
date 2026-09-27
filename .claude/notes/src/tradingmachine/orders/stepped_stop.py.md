# src/tradingmachine/orders/stepped_stop.py

`SteppedStopOrder` mirrors UBI's `stepped_stop` synthetic order type, `unified_broker_interface/utilities/order_engine/stepped_stop.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-27, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row G8 adjustable stop. UBI built the Atlas's group G on 2026-09-27, and this class was added the same day to catch up with it.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

`rules` is passed through as a list of plain dicts, following the rule that vocabulary UBI validates is sent as given rather than wrapped in classes. UBI refuses `trail_points`, `trail_percent` and `activate_at` outside a rule, so the class does not offer them at the top level even though UBI builds it on `trailing_stop`.
