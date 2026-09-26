# src/tradingmachine/orders/freeze_slicer.py

`FreezeSlicerOrder` mirrors UBI's `freeze_slicer` synthetic order type, `unified_broker_interface/utilities/order_engine/freeze_slicer.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row E2 freeze-quantity slicer.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

Only five of UBI's ten brokers publish a freeze limit, each in its own units, and UBI reads the limit of the broker it is actually sending to. When that broker publishes none, the order goes whole, and an exchange refusal is the visible outcome. That is UBI's choice and is not second-guessed here.
