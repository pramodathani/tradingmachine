# src/tradingmachine/orders/cross_instrument.py

`CrossInstrumentOrder` mirrors UBI's `cross_instrument` synthetic order type, `unified_broker_interface/utilities/order_engine/cross_instrument.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row B10 cross-instrument conditional.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI's `CrossInstrument` is a `LimitIfTouched` whose trigger reads another instrument's last traded price, named by `watch_instrument_id`. The class takes the instrument object as `watch_instrument`, as every other part of the library does, and `synthetic_fields()` sends its id under UBI's name. The watched instrument may be any `Instrument`, including an index, because it is only read; the order itself goes to the tradeable instrument the class is built on. `trigger_price` is the level on the watched instrument and is stored as `trigger_level`, for the reason given in the note on `market_if_touched.py`.
