# src/tradingmachine/orders/candle_close_stop.py

`CandleCloseStopOrder` mirrors UBI's `candle_close_stop` synthetic order type, `unified_broker_interface/utilities/order_engine/candle_close_stop.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row B3 candle-close stop.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI's `CandleCloseStop` is a `HiddenStop` with one method overridden, so it takes every hidden-stop field plus `bar_minutes`. The class repeats those fields rather than inheriting from `HiddenStopOrder`, following the user's rule that each case is its own self-contained class.
