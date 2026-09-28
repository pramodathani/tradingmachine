# src/tradingmachine/asset_baskets/index.py

`Index` is the class `EquityIndex.constituents` and every other index's `constituents` return. It also serves an index the user makes up, with no linked instrument.

## Three weightings

`stated` uses each member's weight, as a factsheet gives it. `equal` ignores any weights, which is also what a CSV without a weight column gets. `price` weights by price, which is holding the same quantity of each, the Dow Jones method; its `weights` need live prices and its `_candle_quantities` gives every member the same quantity. A market-capitalisation weighting was not offered, because UBI has no shares-outstanding or free-float data to compute it from.

## `level` needs a base date

`prices` restarts from `base_value` at the first candle of whatever range is asked for, so it cannot report a single level. `level` fixes the quantities at the closes of `base_date`, searching up to ten days forward for the first trading day, and values them at today's last prices. Without a `base_date` it raises `AssetBasketError` rather than inventing one. Verified on 2026-09-28: a price-weighted index of five NIFTY stocks from 2026-01-01 stood at 78.39.

## `to_portfolio`

`to_portfolio` floors each member's share of the capital to whole units at last prices and leaves out a member whose share buys less than one unit. Verified on 2026-09-28: 500,000 rupees in the price-weighted five-stock index gave 83 of each and a value of 497,439.75, the rest being the floored remainders.
