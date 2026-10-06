# src/tradingmachine/orders/plan_parts/marketable_pricing.py

`MarketablePricing` builds UBI's `marketable` pricing, read by `PlanReader` in the sibling project's `unified_broker_interface/utilities/order_engine/utilities/plan_reader.py` and worked out by `marketable_pricing.py` beside it.

## A stale quote also makes it wait (2026-10-06)

UBI's commit `15380c1` of 2026-10-05 makes the rule refuse a quote marked stale as well as an empty book, so the order waits for the next tick. This matters most for an order sent only when a fill arrives, such as an attached hedge, which used to be priced from the stale quote and now waits and tries again on every tick.

This pricing is not the same thing as UBI's `marketable_limit` type, added in the same batch of changes, which is a preset built on `peg` with `on_empty_book: refuse` and is answered HTTP 409 rather than left waiting when the book cannot price it.
