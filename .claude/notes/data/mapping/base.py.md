# data/mapping/base.py

Ported from `unified_broker_interface`'s `back_office/instruments_v2/adapters/base.py`, classification third only. UBI's file also sketched an order/quote/portfolio translation interface; that entire third was not ported because this project's mapping layer is a data layer with no broker API access. The history below is UBI's, carried over because the code here still embodies the lessons.

## The merge mechanism: deterministic UUID5, no matching step

`instrument_id()` hashes the composite natural key (exchange, segment, shape, identity fields) with `uuid5`. Every broker's adapter computes the id independently, so the same instrument from any broker produces the same id and upserts converge on one `instruments.master` row. There is no pairwise matching, no voting, no registry — this is the whole cross-broker merge.

`IDENTITY_NAMESPACE` is a fresh fixed UUID, chosen when this file was written, and deliberately different from UBI's v2 namespace so a tradingmachine instrument id can never alias a UBI v2 id if the two systems are ever compared or combined.

## The Decimal hashing bug, found live at UBI

`canonical_identity_value()` routes every numeric through `Decimal` before stringifying because `str(Decimal('340'))` is `'340'` while `str(float('340'))` is `'340.0'` — two different hash inputs for the same real strike price depending on whether the value came from Postgres (Decimal) or a float cast. Without this, the same instrument hashed differently per source, silently breaking the one guarantee the id design rests on. Floats go through `str()` first to avoid binary-float representation noise.

## The expiry guard, from a live Fyers crash

`to_identity()` raises on a numeric expiry with no explicit transform. A bare number is a raw epoch in some unit that cannot be guessed: pandas assumes nanoseconds for plain numbers, every broker seen so far uses seconds, and Fyers' raw expiry crashed as "year must be in 1..9999" before UBI added this check. Kotak's epochs are worse — they count from 1980-01-01, hence the dedicated `kotak_expiry_epoch` transform rather than a parameterised one.

## The two write hardenings, both from live UBI incidents

1. **Stale rows.** The first version only inserted and updated, never deleted. A broker re-run after a code fix still showed wrong rows from an earlier buggy run of the same (broker, mapping_date), because nothing removed what the previous run produced and the current run does not. `_write_results` now deletes this broker's rows for the mapping date first, inside the same transaction, making every run self-correcting rather than merely idempotent.
2. **Concurrent-writer deadlock.** Multiple adapters writing `instruments.master` at the same time deadlocked when transactions locked overlapping rows in different orders (observed live at UBI). Both row lists are now sorted by instrument id before insert, so every concurrent transaction acquires locks in the same order.

## Config validation, from UBI v1's nse_corporate_bonds bug

UBI v1 had a live example of what happens without load-time validation: seven of ten brokers' NSE bond crosswalk scripts wrote into a table (`nse_corporate_bonds`) that was never part of the declared schema, invisible to every route that iterated the vocabulary. `_validate_config()` fails fast at adapter-load time on any exchange, segment, or shape that is not canonical, which makes that bug class impossible to reintroduce silently. It also enforces the canonical segment ordering (see `segments.py.md`) and requires every rules file to end with the unprefixed `uncategorised` entry on exchange `unknown`, which is the guaranteed fallback for rows whose exchange cannot be determined. `unknown` is not a canonical exchange and is allowed on that one entry only — it is the literal value stored in `instruments.master.exchange` for those rows, since the column is NOT NULL and no real exchange is known.

`_validate_config` accepts both the bare name and the `{exchange}_`-prefixed form when checking segment membership, because the prefixed form is what the YAMLs carry; the prefix is stripped back to the bare name before looking it up.

## Uncategorised routing, the tradingmachine addition

UBI v2 silently skipped rows whose `classify()` returned None. Here `run()` routes them to a catch-all instead: `uncategorised_exchange()` (overridden per broker wherever the raw row carries a usable exchange column) picks the per-exchange bucket, and the unprefixed `uncategorised` entry is the guaranteed fallback. When the row's symbol is blank the broker token becomes the identity symbol, so the id is never computed over an empty field. This keeps coverage measurable — raw rows must equal matched plus uncategorised plus errors — and the full raw row stays recoverable from the broker's raw table by broker, mapping date, and token, which is why no separate capture table with a JSONB payload was built.

## classify_extra, from confirmed dual membership

UBI v1 ran each segment's crosswalk as a fully independent, non-exclusive query, so one raw row could land in two segments legitimately — confirmed with real data on Kotak (a BSE row both a real non-fund-ISIN equity and a crossref-confirmed ETF) and Zerodha (a real instrument in both `bse_equities` and `bse_fixed_income`). `run()` calls `classify_extra()` after `classify()` and writes one row per membership, reproducing that rather than silently picking one.

## Deliberate porting choices

The class is named `BrokerMappingAdapter` rather than UBI's `BrokerAdapter` so it cannot be confused with `data/instruments/base.py`'s `BrokerInstruments`, the raw-ingestion base class. The engine is created in `__init__` from `utilities/configuration` exactly as UBI did, rather than passed in, keeping each adapter self-contained for its `__main__` CLI. The transform dict is module-level and shared (`TRANSFORMS`, un-underscored, since rules YAMLs reference these names by string); broker-local transforms live in the owning adapter's `_field` override rather than being registered globally.
## The seen dates must widen, not overwrite

The first version of the upsert set `last_seen_date = EXCLUDED.last_seen_date` and left `first_seen_date` alone after the initial insert. That is correct only while dates are mapped strictly oldest-first and never revisited, which is not how this pipeline is actually used: a mapping fix is applied by re-running past dates, and the very first build mapped the latest date by hand before backfilling the history behind it.

Both columns were wrong as a result. `first_seen_date` froze at whichever date happened to be written first, so 524,862 of 704,473 rows claimed a first sighting of 2026-09-04 when they had in fact been seen since 2026-08-07. And `last_seen_date` was dragged backwards whenever an older date was mapped after a newer one.

The upsert now widens the range with `LEAST` and `GREATEST`, so both columns are independent of the order dates are mapped in. The stored rows were repaired from `instruments.broker_mappings`, which is the exact record of which instrument was seen on which date.

This was not a cosmetic problem. `crossref.equity_index_symbols` selects the index rows known as of the mapping date, so wrong date ranges made it return almost nothing for past dates — 52 symbols for 2026-08-28 rather than 184 — and the brokers that normalize their index names against it quietly stopped converging on those dates.
