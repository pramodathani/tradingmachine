# src/tradingmachine/orders/liquidity_seeking.py

`LiquiditySeekingOrder` mirrors UBI's `liquidity_seeking` synthetic order type, `unified_broker_interface/utilities/order_engine/liquidity_seeking.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row E9 liquidity-seeking.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

It is the closest anyone can come to the Atlas's impossible minimum-quantity and fill-or-kill orders, which need an atomic fill only an exchange can give.
