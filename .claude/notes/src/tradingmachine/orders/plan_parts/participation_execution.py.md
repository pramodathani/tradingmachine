# src/tradingmachine/orders/plan_parts/participation_execution.py

`ParticipationExecution` mirrors UBI's `ParticipationExecution` in `unified_broker_interface/utilities/order_engine/utilities/participation_execution.py` in the sibling project, read through `PlanReader._read_participation` in `plan_reader.py`, as of 2026-10-02.

Its JSON is `{"participation": {"percent": 10.0, "most_slices": 20}}`. `percent` is required, above zero and at most 100. `most_slices` is a whole number of at least 1 and defaults to 60 in UBI, so the class leaves it out when None.

## Behaviour

On each tick it sends `percent` of the volume traded since its last slice, read from the live quote's cumulative `volume`, counting from when the order starts working. Participation is paced by ticks, so the order starts working, and the count starts, as soon as its trigger holds. A slice that rests unfilled still counts as sent; the unfilled part of a cancelled slice is sent again by later slices, and a slice the broker rejects stops the order.

## Whole lots, fixed on 2026-10-02

UBI's commit `9731fa9` found that a share of volume rarely comes to whole lots, so on a lot-traded contract such as a NIFTY option every slice was refused and the order stalled with nothing sent. Each slice is now cut down to whole lots of the instrument at the chosen broker, or before a broker is chosen the largest lot any broker lists, and a share under one lot leaves the counted volume where it was, so the volume goes on counting towards the next slice. The counters are also restored when a slice is refused. The example `nifty_futures_in_whole_lots.py` prints what a few volumes would send.

## Nesting

Participation is in UBI's `OUTER_NAMES` but not `INNER_NAMES`, so it can release slices for an inner `iceberg`, `twap`, `vwap` or `front_loaded` to work, but cannot itself work the slices of another execution; that pair is refused as `bad_nesting`. It is not accepted by a `using` join, whose pieces must be known in advance.

## Rules that bite

A resting stop cannot be sliced, so stop pricing with this execution is refused as `stop_not_sliced`.
