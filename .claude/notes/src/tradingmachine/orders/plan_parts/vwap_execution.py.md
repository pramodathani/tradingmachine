# src/tradingmachine/orders/plan_parts/vwap_execution.py

`VwapExecution` mirrors UBI's `VwapExecution` in `unified_broker_interface/utilities/order_engine/utilities/vwap_execution.py` in the sibling project, on the shared clock of `timed_slices_execution.py`. It is read by `PlanReader._read_timed` and `PlanReader._read_profile` in `plan_reader.py`, as of 2026-10-02.

Its JSON is `{"vwap": {"slices": 10, "over_minutes": 90, "volume_profile": [...]}}` or `{"vwap": {"slices": 10, "until": "15:00"}}`. `slices` runs from 2 to 60.

## `until` instead of `over_minutes`

VWAP alone of the timed executions takes `until`, a time of day `HH:MM`, given instead of `over_minutes`. The slices are then spread from when the order starts working until that time, and an order that starts after it is refused with HTTP 400 when it begins. Giving both is refused as `bad_setting`, with the message that `until` is "given instead of over_minutes". Both are therefore optional in the class, and the caller supplies exactly one. A `using` join does not accept a VWAP at all, and refuses any timed execution that gives `until`.

## The volume profile

`volume_profile` is a list of relative weights at or above zero, one per half hour from the session's open, which must not be empty and must add up to more than zero. A slice takes the weight of the half hour it falls in, and a slice after the last half hour takes the last weight. UBI's default is `DEFAULT_PROFILE` in `vwap_execution.py`, the NSE equity day's shape, heavy at the open and the close.

## Fixes of 2026-10-02

UBI's commit `42ba13d` changed two things. The half hours are now counted from each segment's own open, through `SessionOpen`: 09:15 for equity and 09:00 for currency and MCX, on the day the order starts working; before, every segment was measured from the equity open. And the default profile is now used only for equity: a currency or commodity order with no profile of its own gets even slices, since the equity shape means nothing for a session with a long evening. A caller who wants a shape for those segments must give `volume_profile`.

## Nesting

VWAP is in both nesting lists, so it can be the outer execution with an inner `iceberg`, which is the usual pairing, or the inner one under `participation`, `iceberg`, `twap`, `front_loaded` or `vwap`.

## Rules that bite

A resting stop cannot be sliced, so VWAP with stop pricing is refused as `stop_not_sliced`.
