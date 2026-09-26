# src/tradingmachine/orders/daily_stop.py

`DailyStopOrder` mirrors UBI's `daily_stop` synthetic order type, `unified_broker_interface/utilities/order_engine/daily_stop.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row B13 daily re-armed stop.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI never resolves references for this type. When the market has opened past the stop, UBI closes the position with a limit rather than placing a stop that fires at whatever the gap left, which UBI's note on `daily_stop.py` explains.
