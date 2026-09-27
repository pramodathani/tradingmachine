# src/tradingmachine/orders/attached_hedge.py

`AttachedHedgeOrder` mirrors UBI's `attached_hedge` synthetic order type, `unified_broker_interface/utilities/order_engine/attached_hedge.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-27, and its parameter names are UBI's field names, except that `hedge_instrument_id` is taken as the instrument object `hedge_instrument`, as `CrossInstrumentOrder` does with its watched instrument.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row G14 attached hedge. UBI built the Atlas's group G on 2026-09-27, and this class was added the same day to catch up with it.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

`ratio` and `delta_volatility` are both optional here and UBI requires exactly one.
