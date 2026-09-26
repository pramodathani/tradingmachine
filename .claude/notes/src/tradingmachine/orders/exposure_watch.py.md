# src/tradingmachine/orders/exposure_watch.py

`ExposureHedgeOrder` reads `watched` as a list of objects, each naming an `instrument_id` and optionally an `exposure_per_unit`, which UBI defaults to 1 (`unified_broker_interface/utilities/order_engine/exposure_hedge.py`). `ExposureWatch` is that object as a class, for the same reason `OrderCandidate` is one: the two field names are documented and spelled right, and the instrument is an object that `document()` turns into an id.

It accepts any `Instrument`, not only a tradeable one, because a watched instrument is only read, never traded. `exposure_per_unit` is where a caller supplies a delta: UBI deliberately has no option pricing model, so the delta half of a delta hedge is the caller's to compute.
