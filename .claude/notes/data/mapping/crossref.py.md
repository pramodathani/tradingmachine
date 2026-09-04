# data/mapping/crossref.py

Ported from `unified_broker_interface`'s `back_office/instruments/crosswalk/crossref.py`. UBI v2's adapters import that v1 module as a live dependency; here it is a first-class part of the mapping package, trimmed to the nine helpers the classification actually uses plus one new one.

## Why it exists

Four brokers — Zerodha, Shoonya, Flattrade, IND Money — carry no ISIN column and cannot self-classify funds, ETFs, investment trusts, or bonds. Without these cross-references, a misfiled row gets a ticker-keyed identity in the wrong segment while an ISIN-bearing broker files the same instrument correctly under a different identity, and the two ids never converge. That is the exact failure the deterministic-id design exists to prevent, so the cross-broker pooling is a deliberate, narrow exception to per-broker independence.

## Porting corrections from UBI's version

Three things differ from the UBI source, all forced by this project's raw tables:

1. Table paths changed from `<broker>.instruments` (one schema per broker at UBI) to `instruments.<broker>` (one schema, one table per broker here).
2. Wisdom Capital's segment column is `exchangesegment` here. One UBI query used `exchange_segment`, which does not exist in this project's table — corrected to `exchangesegment` in the port.
3. Every raw column here is TEXT, where UBI's ingestion inferred native types. Fyers' numeric exchange and segment codes are therefore compared as strings: `exchange = '12'`, `segment = '10'`, `exchange IN ('10', '12')`. Comparing against bare integers would silently match nothing.

## The one UBI dependency replaced

UBI's adapters normalized index names against `master.nse_equity_indices`, a v1 crosswalk output table that does not exist here. The replacement is the new `equity_index_symbols()` helper, which reads this project's own `instruments.master` for `nse_equity_indices` rows with `last_seen_date` equal to the mapping date. It only works because `download_and_map` processes brokers in a fixed order — the index-listing brokers (Dhan first) write their master rows before Zerodha, Shoonya, and Flattrade normalize names against them.

## The live-verification history, from UBI

The docstrings carry UBI's discovery history because these queries still depend on it:

- `known_bse_fixed_income_symbols`: government security naming has too many variants for a regex, discovered live on 2026-08-30 building UBI's Zerodha BSE equities script; Kotak's ISIN-verified 'F'/'G' groups are the reliable signal.
- `known_nse_fund_symbols`: Kotak's own 'EQ' group leaked an INF-prefixed ETF ticker ("SILVERADD-EQ") on NSE, so group codes alone cannot discriminate.
- `known_nse_investment_trust_symbols`: sourced from Dhan rather than Kotak because Kotak's 'IV'/'RR' groups produced an apparent "IRBIT" vs "IRBINVIT" mismatch that turned out to be two genuinely distinct trusts; Dhan's spellings matched Fyers exactly.
- `known_nse_fixed_income_symbols`: Dhan's bond `underlying_symbol` is the issuer's *name*, which collides with that issuer's real equity ticker (MOTHERSON, CHOLAFIN, ELECTCAST) — so this set may only build the fixed-income segment, never exclude rows from equities.
- `known_nse_etf_symbols`: the genuine-ETF discriminator is the plain-equity series within a fund tag, verified as an exact 349-symbol match across Dhan/Fyers/Kotak/Wisdom Capital, with Stoxkart adding two bond ETFs and Groww adding stray "-EQ" suffixes that get stripped.
- `known_bse_etf_symbols`: union of the three brokers whose 'E' fund group carries only real ETFs (43 Gold/Silver rows) plus 2-of-N broker name-voting — a single broker's '%etf%' name match trips on real companies whose names contain "ETF" (Wisdom Capital's freight company), while every genuine 2-broker match carried an INF fund ISIN with zero exceptions.
- `security_id_to_isin`: the exchange-assigned security-id scheme is shared across Dhan/Kotak/Fyers/Groww/Stoxkart/Wisdom Capital, confirmed live at 100% resolution of the ISIN-less brokers' fixed-income buckets; first-seen-wins on disagreement affects 21 of 35,628 entries, never a genuinely different security.
## The date test, and why it is a range

`equity_index_symbols` asks whether an index was known **as of** the mapping date, using `first_seen_date <= date <= last_seen_date`, rather than whether it was last seen exactly on it. The two are the same thing only while the mapping date is the most recent one mapped, which stops being true the moment any past date is re-run. Testing the last seen date alone made the helper return almost nothing for a past date, and the brokers that normalize their index names against it silently kept their own spellings instead of converging.

The range test depends on the seen dates being right, which in turn depends on the upsert widening them rather than overwriting — see `base.py.md`.
