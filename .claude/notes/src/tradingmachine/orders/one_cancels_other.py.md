# src/tradingmachine/orders/one_cancels_other.py

`OneCancelsOtherOrder` mirrors UBI's `oco` synthetic order type, `unified_broker_interface/utilities/order_engine/oco.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row D2 one-cancels-other.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

`transaction_type` is the side that opened the position, not the side of the exits, which reads backwards the first time: a long is protected by asking for `buy`. UBI reduces the surviving exit by what the other filled rather than cancelling it, which is the Atlas's D3 one-updates-other, so there is no separate class for D3. The double fill that no exchange can prevent is recorded in UBI's `.claude/notes/unified_broker_interface/utilities/order_engine/oco.py.md`.
