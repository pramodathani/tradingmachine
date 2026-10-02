# src/tradingmachine/orders/plan_parts/freeze_limit_execution.py

`FreezeLimitExecution` mirrors UBI's `FreezeLimitExecution` in `unified_broker_interface/utilities/order_engine/utilities/freeze_limit_execution.py` in the sibling project, and the `freeze_limit` branch of `PlanReader._read_execution_value` in `plan_reader.py`, as of 2026-10-02. UBI's `freeze_slicer` preset is this execution and nothing else.

Its JSON is `{"freeze_limit": {}}`, and UBI refuses any setting inside it as `unknown_setting`.

## Behaviour

The broker is chosen first, through UBI's selector, because each broker publishes its freeze quantity in its own units: for one MCX silver option, brokers with a lot of 30 report 600 and brokers with a lot of 1 report 20, both meaning twenty lots. The order's quantity in that broker's terms is compared with its figure and split evenly into orders each within it, all sent at once to that broker, which is kept in the execution's memory. A broker that publishes no freeze quantity gets the order whole, and more than 20 slices is refused.

## Rules that bite

UBI's documentation says it is one execution among the others rather than applied inside every piece, because it sends every piece at once to one broker, and it is in neither nesting list. So an order above the freeze quantity that should also be spread over time cannot be built. A resting stop cannot use it.
