# marketable_limit.py

`MarketableLimitOrder` was added on 2026-10-06 for UBI's fifty-fifth type, `marketable_limit`, which UBI built in its commit `462c6c1` (pull request #74). It is not an Atlas row. UBI made it so that a market order could no longer fill far from the price that was showing, and because brokers such as Flattrade refuse market orders sent through an API with `ALGO_CHK: MKT Order type not allowed for API order`.

UBI routes the type into a plan of its preset: a `peg` on `opposite_touch` with `offset_ticks` of minus `buffer_ticks` and `on_empty_book` `refuse`, plus a `lifetime` of `fill_within_seconds / 60` minutes that cancels. A dry run of the type shows exactly that plan. The class is needed only to choose other values, because UBI already runs every plain `market` body with no `synthetic` object and `after_market` False as this type with the defaults, while `UNIFIED_BROKER_INTERFACE_API_ORDER_MARKET_AS_LIMIT` is on.

Both settings are sent as given or left out when None, following the rule that UBI checks order fields: UBI refuses a `buffer_ticks` that is not a whole number at or above zero, and a `fill_within_seconds` that is not above zero, with HTTP 400.

The live run on 2026-10-06 at 09:13, in the pre-open session, was accepted by UBI and rejected by the exchange; the run at 09:15 filled one Vodafone Idea share at 12.78, the best offer, and the parent ended `completed`.

## maximum_cost_bps and reaches_size, added on 2026-10-31

UBI added both settings to the type, and to the `peg` pricing it is built from, on 2026-10-07, in its commits `63e3d68` and `102da2e`. This class caught up with them on 2026-10-31.

`maximum_cost_bps` has the engine run its pre-trade estimate just before sending, walking the whole quantity through the five visible levels, and refuse the order with HTTP 409 when the cost in basis points of the midpoint is above the maximum or when the visible levels do not hold the whole quantity. UBI calls the guard cautious, because the order itself is only `buffer_ticks` past the best price and would rest whatever the first levels cannot fill, so it refuses some orders that would only have rested part of their quantity. A dry run does not run the estimate, so it cannot show the refusal.

`reaches_size` sets the limit no nearer than the deepest visible level the unfilled quantity reaches, up to the fifth, and does the same on each repricing tick for what is still unfilled. UBI's example book offers 100 at each price from 1000.05 to 1000.25: a buy of 10 stays at 1000.15, a buy of 350 goes to 1000.20, and a buy of 600 to 1000.25.

Both default to UBI switches that `PlanRouting` writes into every `marketable_limit` that does not set its own, which includes every plain market order: `UNIFIED_BROKER_INTERFACE_API_ORDER_MAXIMUM_COST_BPS`, unset, and `UNIFIED_BROKER_INTERFACE_API_ORDER_MARKET_REACHES_SIZE`, off. That is why `reaches_size` is `bool | None` here rather than `bool = False`: None leaves the switch in charge, and False is the only way to turn it off for one order while the switch is on. Neither value is checked locally, because UBI refuses a `maximum_cost_bps` that is not a number above zero, and a `reaches_size` that is not a boolean, with HTTP 400.

`synthetic_fields` had no `Examples:` section until the same day, and it gained two.
