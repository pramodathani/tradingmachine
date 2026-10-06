# src/tradingmachine/orders/attached_hedge.py

`AttachedHedgeOrder` mirrors UBI's `attached_hedge` synthetic order type, `unified_broker_interface/utilities/order_engine/attached_hedge.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-27, and its parameter names are UBI's field names, except that `hedge_instrument_id` is taken as the instrument object `hedge_instrument`, as `CrossInstrumentOrder` does with its watched instrument.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row G14 attached hedge. UBI built the Atlas's group G on 2026-09-27, and this class was added the same day to catch up with it.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

`ratio` and `delta_volatility` are both optional here and UBI requires exactly one.

## UBI's fixes of 2026-10-05, recorded on 2026-10-06

UBI's commit `15380c1` fixed several ways an attached hedge fell out of step with its entry. The hedge stopped growing once all its broker orders had filled, so later entry fills went unhedged while the parent ended `completed`; it now grows again. An `ioc` hedge the exchange cancelled was sent again at once in a loop; it now waits for the next entry fill. A caller's change to a hedge order's quantity used to be modified straight back and is now kept. An entry that finished with less than one lot of hedge to send used to leave the parent `working` for ever; it now completes. A stale hedge quote or a delta with no forward price now waits and is retried on every tick. A refused hedge now cancels the rest of the entry and ends the parent `failed` instead of `completed` with the position unhedged, and naming the entry's own instrument as the hedge is refused with HTTP 400, because the engine had bought 1,000 RELIANCE and sold the same 1,000 straight back.
