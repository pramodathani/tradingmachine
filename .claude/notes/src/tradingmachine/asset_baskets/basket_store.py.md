# src/tradingmachine/asset_baskets/basket_store.py

The user left the choice of database to Claude on 2026-09-28. MongoDB was chosen over TimescaleDB for three reasons: `Configuration` already builds `mongodb_connection_string` and the UBI client already reads its settings from the same database, `pymongo` is already a declared dependency while PostgreSQL would need `psycopg2`, which is only in `requirements.txt`, and one basket, a name with a list of members, fits naturally in one document rather than in two tables.

## One document per version

A document is identified by `name` and `effective_date`, with a unique index on the pair, because an index is rebalanced every half year and a fund's holdings change every month, and the user may want to know what a basket held on a past day. `load` finds the latest version on or before `as_of`. Dates are stored as `YYYY-MM-DD` text so that MongoDB's `$lte` compares them correctly as strings. `save` replaces a version stored for the same date, so importing a corrected file for the same day overwrites the mistake rather than raising.

The indexes are created on every `save`, which MongoDB treats as a no-op when they exist; there is no separate setup step for the user to remember.

## Rebuilding the right class

`build` reads `kind` and picks the class with a plain `if` chain, which the user's rules prefer over a lookup table or dynamic dispatch. Every member is rebuilt in one `POST /api/instruments/details`. The linked instrument is looked up separately unless the caller already has it, which is what `constituents` passes, so `nifty.constituents.linked_instrument` is the very `EquityIndex` object it was read from.

## Verified on 2026-09-28

A five-stock index imported from a CSV and linked to NIFTY was saved, listed by `names` and `history`, read back through `nifty.constituents` as an `Index` linked to the same `EquityIndex`, and deleted, after which `nifty.constituents` returned None. The same round trip worked for an `ExchangeTradedFundConstituents` linked to NIFTYBEES. Nothing from the tests was left in the collection.
