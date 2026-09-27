# src/tradingmachine/orders/underlying_peg.py

`UnderlyingPegOrder` mirrors UBI's `underlying_peg` synthetic order type, `unified_broker_interface/utilities/order_engine/underlying_peg.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-27, and its parameter names are UBI's field names, except that `watch_instrument_id` is taken as the instrument object `watch_instrument`, as `CrossInstrumentOrder` does.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row G6 pegged-to-stock. UBI built the Atlas's group G on 2026-09-27, and this class was added the same day to catch up with it.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI builds it on its `peg` type, but the documentation lists only these five fields for it, so `reference`, `offset_ticks` and `cap_price` are not offered.
