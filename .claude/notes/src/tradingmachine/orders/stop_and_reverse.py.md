# src/tradingmachine/orders/stop_and_reverse.py

`StopAndReverseOrder` mirrors UBI's `stop_and_reverse` synthetic order type, `unified_broker_interface/utilities/order_engine/stop_and_reverse.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-27, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row G13 stop-and-reverse. UBI built the Atlas's group G on 2026-09-27, and this class was added the same day to catch up with it.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

In the price-trigger types UBI's `synthetic.trigger_price` is the touch level, not the order's own trigger. The class takes it as `trigger_price`, because that is UBI's name, stores it as `trigger_level` so it cannot be mistaken for the template's `trigger_price` attribute, and does not accept an order trigger at all.

As for `CloseOnTriggerOrder`, which UBI builds it on, the template's `quantity` is required but ignored, because the engine acts on the net position held when it fires.
