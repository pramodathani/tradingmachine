# src/tradingmachine/orders/scale_with_profit_taker.py

`ScaleWithProfitTakerOrder` mirrors UBI's `scale_with_profit_taker` synthetic order type, `unified_broker_interface/utilities/order_engine/scale_with_profit_taker.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-27, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row G15 scale with profit-taker. UBI built the Atlas's group G on 2026-09-27, and this class was added the same day to catch up with it.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI builds it on its `ladder` type, so `from_price`, `to_price` and `steps` carry the ladder's own limits and descriptions. It never finishes on its own, which is why the class docstring points at `cancel()`.
