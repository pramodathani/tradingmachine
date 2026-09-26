# src/tradingmachine/orders/exposure_hedge.py

`ExposureHedgeOrder` mirrors UBI's `exposure_hedge` synthetic order type, `unified_broker_interface/utilities/order_engine/exposure_hedge.py` in the sibling project. Its settings, their defaults and their limits were taken from `../unified_broker_interface/docs/rest-api/synthetic-orders.md` on 2026-09-26, and its parameter names are UBI's field names.

In the Synthetic Order Atlas that UBI's engine was designed from, it is row F4 delta or exposure-triggered hedge.

It checks none of its settings before sending, following the rule that UBI holds the order rules; UBI's engine checks each field when it builds the order and answers HTTP 400 naming the one that is wrong, and a dry run shows that without sending anything.

UBI's `ExposureHedge` reads `watched`, `lower_band`, `upper_band`, `hedge_instrument_id` and `hedge_exposure_per_unit`, and works out the side and quantity of every hedge itself. The class is built on the hedge instrument, which becomes both the body's `instrument_id` and `hedge_instrument_id`, so the two can never disagree. The template's side, order type and quantity are placeholders, `buy`, `market` and 1, because the route validates them before the engine overwrites them. UBI's note says the delta half of the Atlas's F4 delta hedge is deliberately not built, since the engine has no option pricing model, so an option's delta is supplied as its `exposure_per_unit` on `ExposureWatch`. An exposure hedge is armed and waits, so it survives a flatten; This project's former Known issues page, which the documentation rebuild of 2026-09-26 removed and which `git show b5761c0:docs/contributing/known-issues.md` still prints records that UBI's kill switch does not disarm engine parents.
