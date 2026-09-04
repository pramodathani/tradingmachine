# data/mapping/verify_mapping.py

The report that says whether the mapping is right. It never raises on a finding: the point is to see the whole picture at once, and a check that stopped at the first problem would hide the four behind it. That philosophy matches `check_row_count_deviation` on the download side.

## Why these seven, in this order

Each check would explain a failure in the one after it, so reading top to bottom finds the root cause first.

**1. Coverage.** Every raw row must end up either classified or in an uncategorised bucket. This is the check the uncategorised buckets exist to make possible: UBI dropped unmatched rows silently, so there was no number that could be reconciled. Note that the mapped counts here are distinct instruments, so they sit below the raw count wherever a broker lists one instrument on several rows; the run summary printed by each adapter is the row-for-row reconciliation, and it is exact.

**2. Convergence.** The distribution of how many brokers carry each instrument, plus a hand-checked spot list. Cash equities should show thousands of instruments carried by eight or more brokers. If a broker's rules break, its share of the high-broker-count buckets collapses and this is where it shows.

**3. Duplicates.** Tokens pointing at more than one instrument on one date. Some are genuine — a row with two segment memberships is deliberate on Kotak and Zerodha — so each finding is printed rather than treated as failure.

**4. Index names.** The check that catches an alias leak. Every normalized index name should have exactly one spelling; two spellings mean one real index has two identities and the brokers carrying it are not merging. This is the most fragile part of the whole design, because it depends on the processing order and on per-broker alias tables.

**5. Round-trips.** A random sample of stored mappings resolved in both directions. A forward miss — an identity that does not return the token it was built from — is always a bug in the hashing or the write. A backward miss is expected where a broker reuses one token across instruments, since the look-up answers with one of them by design.

**6. Backfill sanity.** Per-date instrument counts across the whole history, with the change from the previous date, plus the first and last seen extremes. A sudden drop on one date usually means a truncated broker file upstream rather than a mapping fault, which is why the broker count per date is printed beside it.

**7. Uncategorised profile.** Where each broker's unclassified rows landed. This is the alarm that keeps the catch-all buckets honest: a bucket that suddenly grows is a rules gap, and without this check it would look like success. Expectations are per broker, not global — Stoxkart legitimately runs near 7% because it publishes spreads and duplicate rows that no other broker does, while Shoonya runs near 0.05%.

## What the first full run found, on 2026-09-04

Every finding turned out to be the brokers' own data rather than a mapping fault, and the checks were sharpened afterwards so that the report says which is which rather than leaving a large number unexplained.

**Coverage** reconciled for all ten brokers. Uncategorised share ranged from 0.06% (Shoonya) to 1.61% (Stoxkart), with the run summaries reconciling row for row.

**Convergence** put 39,982 instruments under all ten brokers and 64,889 under nine. RELIANCE and HDFCBANK resolved to ten brokers each, NIFTY and BANKNIFTY to nine — Wisdom Capital does not publish NSE index spot rows — and SENSEX to seven.

**Duplicate tokens** looked alarming at 68,394 pairs until the check was split by cause. A broker's token space is per exchange segment rather than global, so 16,887 of those are one number meaning different things on different markets, and 51,232 more span two segments, which is the dual membership the design deliberately keeps. That leaves 275 inside a single segment, all Flattrade, and those are company renames: its file carries both the old and the new symbol against one token, so "GMRINFRA" and "GMRAIRPORT" are both listed. Name-based identity necessarily gives those two identities, and only the current name converges with the other brokers. That is a fact about the data, not something the mapping can fix.

**Index names** showed no normalized name with two spellings, which is the alias tables and the processing order working.

**Round-trips** matched 1,000 of 1,000 in the identity-to-token direction. Thirty-nine of 1,000 came back naming a different instrument in the other direction, and after adding a follow-up query, all thirty-nine were on tokens the broker genuinely reuses — none unexplained. That follow-up is now part of the check: a backward miss on a token that is *not* reused has no innocent explanation and is reported separately.
