# src/tradingmachine/asset_baskets/member_resolver.py

`MemberResolver` was not in the plan's file list. It was added because three places need the same step, turning rows that name instruments into members: `BasketStore.build`, `BasketCsvImporter` and `Portfolio.from_holdings` and `from_positions`. One small class does it once.

## One request for the whole basket

`resolve` sends every row to `POST /api/instruments/details` at once and builds each instrument from its entry through the new `details` argument of the instrument constructors. A 50-member index costs one request rather than fifty. An index row becomes a `NonTradeableInstrument` and anything else a `TradeableInstrument`; the member does not need the family class, such as `Equity`, for anything a basket does.

## Failures are collected, then raised together

A row UBI cannot find does not stop the others from being looked up, but `resolve` raises one `BasketMemberError` naming every failed row at the end. A basket silently missing a member would give wrong weights, so a partial basket is never returned. Verified on 2026-09-28: a list with `INFY` and `NOSUCHSTOCK` raised `UBI could not find 1 of 2 instruments: {'exchange': 'nse', 'segment': 'equities', 'symbol': 'NOSUCHSTOCK'}: no instrument nse_equities NOSUCHSTOCK is mapped on 2026-09-28`.

A row with an `instrument_id` is looked up by that alone, because UBI's list route takes either an id or the identity fields, and a stored basket always has the id.
