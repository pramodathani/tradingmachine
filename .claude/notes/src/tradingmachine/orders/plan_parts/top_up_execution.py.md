# src/tradingmachine/orders/plan_parts/top_up_execution.py

`TopUpExecution` mirrors UBI's `TopUpExecution` in `unified_broker_interface/utilities/order_engine/utilities/top_up_execution.py` in the sibling project, and the `top_up` branch of `PlanReader._read_execution_value` in `plan_reader.py`, as of 2026-10-02.

Its JSON is `{"top_up": {}}`, and UBI refuses any setting inside it as `unknown_setting`.

## What it is for

It only makes sense for an order whose size a join changes, such as the `each_fill` child of a `ThenPart`. Each time the target grows, one new broker order is sent for the quantity neither traded nor resting, so every broker order keeps the price it was given and its place in the queue; the default `all_at_once` would modify its one resting order instead. A target that shrinks cuts resting orders, newest first. A cancelled or rejected order stops it until the target next grows, as described in the section below.

UBI's `attached_hedge` and `legged_spread` presets use it for their second leg, which is why the example `calendar_spread_legged_in.py` writes a legged calendar spread out with it.

## Rules that bite

It is in neither nesting list, and a resting stop cannot use it, since a stop may only be `all_at_once` or `daily`.

## A cancelled order no longer comes straight back (2026-10-06)

Until UBI's commit `15380c1` of 2026-10-05, two things went wrong with a top-up order. Once all of its broker orders had filled it stopped growing, so later fills of an entry went unhedged while the parent ended `completed`. And a cancelled order was sent again at once, so an `IOC` hedge that the exchange cancelled unfilled was followed by another, and three cancellations gave four orders. UBI now reopens a filled top-up order whenever its target grows, and treats a cancelled order like a rejected one, ending the order until the first plan next fills, so what is missing is still sent but only once per fill. A rejection still ends it for good, and the parent then ends `failed` because the entry is left without its hedge. A caller's change to a hedge order's quantity is kept rather than modified back. The docstring was brought in line on 2026-10-06; it had said that a cancelled order's unfilled part is sent again.
