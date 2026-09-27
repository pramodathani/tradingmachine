# src/tradingmachine/orders/account_conditional.py

`AccountConditionalOrder` mirrors UBI's `account_conditional` synthetic order type, `unified_broker_interface/utilities/order_engine/account_conditional.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-27, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row G17 account-conditional. UBI built the Atlas's group G on 2026-09-27, and this class was added the same day to catch up with it.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI builds it on its price-trigger base, but it watches the account rather than a price, so it takes no `trigger_price`, `trigger_on` or `hold_seconds`, and `trigger_direction` is required rather than defaulted from the side.
