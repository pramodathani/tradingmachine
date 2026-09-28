# src/tradingmachine/asset_baskets/portfolio.py

`Portfolio` is a basket counted in units. It overrides `weights` with each member's share of today's value, divided by the gross value so a short position shows as a negative weight, and `_candle_quantities` with the real quantities, so its candles show what today's holdings were worth at each past candle.

## Built from the account

`from_holdings` reads `GET /api/portfolio/holdings` and `from_positions` reads `GET /api/portfolio/positions`, then resolves every instrument in one list request. A position held under two products, such as intraday and carry, becomes one member with the total quantity and no average price, because two average prices cannot be combined without the two quantities' cost, and a member may appear only once.

Verified on 2026-09-28: `from_holdings` built seven members and valued them at 9,240.43 rupees, against UBI's summary of 9,237.33, with an invested value of 11,216.62 against UBI's 11,216.99. The value differs because the portfolio prices at the live last price while UBI's summary uses the prices in its holdings document; the invested value differs because UBI adds the brokers' own invested figures, while the portfolio multiplies quantity by average price. `from_positions` raised `BasketMemberError: No position is open`, which was true.

## Orders go in UBI's list form, not the basket order

`place_orders` and `rebalance` send one `POST /api/orders/place` with `{"orders": [...], "dry_run": ...}`. UBI's `basket` synthetic order was rejected for this, because it takes at most 25 legs and sends every leg to the first leg's broker, so a NIFTY portfolio of 50 would not fit. The list form takes up to 500 orders and places them in parallel, each at the broker that suits it. `dry_run` goes beside the list, never inside an order, which UBI refuses. The request gets a 60-second timeout because UBI waits up to 25 seconds for the engine's answers.

Only market orders are sent. A limit order would need one price per member, which a portfolio does not have, and a plain limit order would be held by UBI's engine rather than sent. Each answer's `broker` is kept in the table, because a dry run shows which broker each order would go to.

## Rebalancing is computed here

The saved rule is that order logic belongs in UBI. Rebalancing to target weights is portfolio arithmetic that UBI does not offer, so it is built here, as the plan said; it could move into UBI later as a `quantity_reference`. Quantities are floored towards zero to whole units and sent as computed, with no lot or tick check, following the no-local-validation rule. `rebalance_trades` is separate from `rebalance` so the trades can be read before anything is sent.

## Not yet tested with real orders

The dry run of `place_orders` for a five-member portfolio built by `Index.to_portfolio` returned an entry per order with an `intent_id` and the broker's request. The real-order test the plan calls for, one unit each of two cheap shares during market hours, has not been run, because the work was done after the market closed.
