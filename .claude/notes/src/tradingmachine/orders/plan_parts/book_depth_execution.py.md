# src/tradingmachine/orders/plan_parts/book_depth_execution.py

`BookDepthExecution` mirrors UBI's `BookDepthExecution` in `unified_broker_interface/utilities/order_engine/utilities/book_depth_execution.py` in the sibling project, read through `PlanReader._read_book_depth` in `plan_reader.py`, as of 2026-10-02. It is the plan's form of the fixed `liquidity_seeking` type.

Its JSON is `{"book_depth": {"limit_price": 1000.0, "minimum_quantity": 500}}`. Both are required: `limit_price` is a positive price and `minimum_quantity` a whole number of at least 1.

## Behaviour

It sends nothing until the displayed quantity at every level of the other side of the book no worse than `limit_price` adds up to at least `minimum_quantity`, and then strikes for the smaller of what is shown and what is left. A strike that partly fills rests at its price; later strikes are only for what is neither traded nor resting. A strike the broker rejects stops the order. The size shown is the size displayed, so more or less may fill. It reads quotes and is paced by ticks, so it starts watching as soon as the trigger holds.

## Pricing

The execution decides when and how much, but the strike's price is the order's pricing. UBI's `liquidity_seeking` preset pairs it with `fixed` pricing at `limit_price`, and the examples here do the same with `FixedPricing(price=limit_price, order_type="LIMIT")`, so a strike that does not fill rests at the limit. Nothing stops a caller pairing it with another pricing, and UBI does not refuse that.

## Rules that bite

It is in neither nesting list, so it cannot be half of a nested pair, and a resting stop cannot use it.
