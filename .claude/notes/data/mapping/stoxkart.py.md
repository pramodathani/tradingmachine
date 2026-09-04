# data/mapping/stoxkart.py

Ported from UBI's `back_office/instruments_v2/adapters/stoxkart.py`, classification side only — the order, quote, and portfolio methods were not ported (data layer only). This is the heaviest adapter in the project; the rules file is `rules/stoxkart.yaml`.

## The classification pipeline

`classify` runs three stages rather than the usual one:

1. **Early checks** (`_classify_early`), before the rules engine. These claim the segments whose real condition is a winner set, a crossref allowlist, or a regular expression, and they must win over any rule listed for a different segment that would otherwise match the same row first.
2. **The rules engine**, then `_post_filter`, which applies the exclusions and redirects that only make sense once a rule has matched.
3. **Fallback checks** (`_classify_fallback`) for the segments with no rules at all, reached only when nothing else matched.

## The four winner sets

Stoxkart's raw file lists the same instrument more than once, in four different ways, and no row-local rule can tell a winner from a loser. Each set is computed once per run with an explicit loop over the day's rows:

- **NSE equities**: one row per symbol, chosen by series priority (EQ first, then T0, BE, ST and the rest), among rows with a real non-fund ISIN.
- **BSE equities**: one row per symbol, preferring any series over NS and NT, after dropping symbols ending in `#` and fund-ISIN rows in the leaky A and B series.
- **BSE fixed income**: one row per ISIN. The file carries a normal F or G series row plus FC and GC odd-lot duplicates with lot sizes in the hundreds of thousands — UBI found the stored token for the same bond flipping between 440066 and 800178 from one date to the next because nothing chose between them. Normal series wins, lowest token breaks the tie. Tokens are text in this project's raw tables, so the tie-break sorts numerically through `token_sort_key` rather than lexically, which would order 800178 before 9.
- **MCX options**: one row per contract, highest token wins.

Rows that lose one of these races return None from `classify` and land in that exchange's uncategorised bucket, where they are counted. UBI dropped them silently.

## The regular expressions

The BSE currency and fixed income derivative segments mix single-leg contracts, calendar spreads, and reference rows inside one instrument type, with no marker column. Only the description tells them apart, so a single-leg pattern is matched against it. The NSE side is easier: its spreads carry an `SP-` description prefix, so those are excluded by prefix rather than by pattern. NCDEX futures spreads are detected by a description pattern with two month names.

## The redirects

- An `nse_equities` row with an INF-prefixed ISIN is an exchange traded fund, and one with no ISIN at all and series EQ is an index. Both are redirected rather than dropped: UBI originally dropped them, which starved both target segments completely, because `nse_equities`' rule and the two real conditions share the same series list.
- An `nse_fixed_income_futures` row on the ONMIBOR underlying is a rate index future, redirected to `nse_fixed_income_index_futures`.

## The two-source segments

`nse_fixed_income` merges two disjoint raw sources into one canonical segment: NSE cash-market bonds, identified by ISIN and carrying real lot and tick values with the tick in hundredths, and NSECD rate underlyings, identified by symbol and carrying no meaningful sizes. `to_identity` and `to_broker_fields` both branch on the raw exchange column for this reason. `ncdex_commodity_indices` is a similar two-source merge (SPOT index names and EQTY rows), but simpler, since both use the description as the identity.

## The deliberate error

`ncdex_commodity_options` raises when a row's expiry, strike, or option type is unparseable or missing. The base class catches that per row and counts it as an error, which is the intended outcome: a corrupt option row must not be written under a mis-identified id. No special mechanism, just the existing one.

## Expected uncategorised profile

Stoxkart's uncategorised share is by far the highest of any broker, around 7% of raw rows, and it is expected rather than a rules gap. Verified against the 2026-09-04 snapshot, the 34,549 unmatched rows were: 14,092 BSE currency spread contracts, 8,262 duplicate MCX option rows, 3,607 NSE stock future spreads with the `SP-` prefix, 1,500 BSE F-series mutual fund rows, 1,335 NCDEX spread futures, 1,247 NSE currency spreads, and a long tail of series-priority losers and reference rows. Every one of these was dropped silently by UBI. A verification alarm on this broker should therefore be set against that profile, not against a low absolute threshold.
