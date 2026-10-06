# marketable_limit.py

`MarketableLimitOrder` was added on 2026-10-06 for UBI's fifty-fifth type, `marketable_limit`, which UBI built in its commit `462c6c1` (pull request #74). It is not an Atlas row. UBI made it so that a market order could no longer fill far from the price that was showing, and because brokers such as Flattrade refuse market orders sent through an API with `ALGO_CHK: MKT Order type not allowed for API order`.

UBI routes the type into a plan of its preset: a `peg` on `opposite_touch` with `offset_ticks` of minus `buffer_ticks` and `on_empty_book` `refuse`, plus a `lifetime` of `fill_within_seconds / 60` minutes that cancels. A dry run of the type shows exactly that plan. The class is needed only to choose other values, because UBI already runs every plain `market` body with no `synthetic` object and `after_market` False as this type with the defaults, while `UNIFIED_BROKER_INTERFACE_API_ORDER_MARKET_AS_LIMIT` is on.

Both settings are sent as given or left out when None, following the rule that UBI checks order fields: UBI refuses a `buffer_ticks` that is not a whole number at or above zero, and a `fill_within_seconds` that is not above zero, with HTTP 400.

The live run on 2026-10-06 at 09:13, in the pre-open session, was accepted by UBI and rejected by the exchange; the run at 09:15 filled one Vodafone Idea share at 12.78, the best offer, and the parent ended `completed`.
