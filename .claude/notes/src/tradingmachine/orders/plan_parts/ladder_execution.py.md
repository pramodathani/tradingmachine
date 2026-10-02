# src/tradingmachine/orders/plan_parts/ladder_execution.py

`LadderExecution` mirrors UBI's `LadderExecution` in `unified_broker_interface/utilities/order_engine/utilities/ladder_execution.py` in the sibling project, read through `PlanReader._read_ladder` in `plan_reader.py`, as of 2026-10-02.

Its JSON is `{"ladder": {"from_price": 1000.0, "to_price": 990.0, "steps": 5}}`. All three are required. The two prices must differ, and `steps` is a whole number from 2 to 20.

## Behaviour

Every rung is sent at once, as limits evenly spaced from `from_price` to `to_price`, each rounded to the tick on the passive side, so a range that does not divide evenly into ticks gives rungs that rest rather than cross. The quantity is shared as evenly as whole units allow, the first rungs taking the remainder, so 100 over three rungs is 34, 33 and 33. A quantity smaller than `steps` is refused when the order is sent.

## Pricing

The rung prices replace whatever the order's pricing set, so the examples give a ladder no pricing. Inside a `using` join, which accepts `ladder` with `twap` and `front_loaded`, UBI goes further and refuses any pricing on either the order or `each_piece` as `using_ladder_priced`.

## Rules that bite

It is in neither nesting list, and a resting stop cannot use it.
