# src/tradingmachine/orders/volatility.py

`VolatilityOrder` mirrors UBI's `volatility` synthetic order type, `unified_broker_interface/utilities/order_engine/volatility_order.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-27, and its parameter names are UBI's field names, except that `watch_instrument_id` is taken as the instrument object `watch_instrument`, as `CrossInstrumentOrder` does.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row G7 volatility order. UBI built the Atlas's group G on 2026-09-27, and this class was added the same day to catch up with it.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

The module is `volatility`, after UBI's registry name, rather than `volatility_order`, UBI's own file name, because every module here is named after the type it sends and the class name already ends in `Order`. UBI builds it on `underlying_peg`, and the documentation says it takes the same `lowest_price`, `highest_price` and `step_ticks`, so those are offered too.
