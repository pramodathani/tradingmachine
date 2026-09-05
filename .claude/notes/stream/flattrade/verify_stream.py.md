# stream/flattrade/verify_stream.py

## Why the REST half is a copy of Dhan's and not a shared module

The `--against-rest` flow — select instruments spanning the exchange codes, capture ticks on one connection, fetch the broker's own quotes, compare field by field, measure the implied scale — is the same job Dhan's `verify_stream.py` does, and it is written out again here rather than shared. The two differ in every place a shared helper would need arguments for: Dhan posts batches of securities to one endpoint, Flattrade prices one instrument per request with `jData`/`jKey`; Dhan's quote response carries a full OHLC block and open interest, Flattrade's carries last, high, low, volume and depth but no open, no close and no open interest; and Dhan needs a binary capture loop while this one merges partials through `TickAssembler`. The user's standing preference is duplication over abstraction for cross-broker work.

## What the quote endpoint can and cannot settle

`GetQuotes` takes one instrument per call — form fields `jData={"uid":...,"exch":...,"token":...}` and `jKey=<session token>` — and answers with `stat`, `lp`, `h`, `l`, `v`, `ltq`, `bp1..5`, `bq1..5`, `sp1..5`, `sq1..5` and `pp`. It has no open, no close and no open interest, so those contract fields go uncompared in this mode and the implied-scale measurement uses `lp` instead of the close price Dhan's version uses. A one second pause separates requests because the run needs a handful of instruments and a read-only endpoint should not be hammered.

`VERIFICATION_TOLERANCE` is 0.011, so a one paisa difference counts as agreement. The first version of the comparison check tried a one paisa wrong quote and correctly produced no disagreement — the tolerance was doing its job. The check now uses a full rupee for the mismatch scenario.

## The exchange code translation is pinned, not derived

Flattrade's six scrip-master codes, confirmed live against the instrument tables, are NSE, BSE, NFO, BFO, CDS and MCX. The mapping is: equities and indices on their cash exchange, NSE derivatives on NFO, BSE derivatives on BFO, currency derivatives on CDS for both exchanges, commodities on MCX. BSE equity indices map to BSE on the theory that BSE's index touchlines subscribe on the cash exchange; that is a live-run question the first session either confirms or corrects. Exchange traded funds, investment trusts and the uncategorised remainder map to None and are skipped — they are tradable in principle but add nothing the equities samples do not already cover, and the illiquid ones produce empty comparisons.

`check_exchange_code_translation` pins every mapping to its literal because the translation and the subscription are the only places this module makes a routing decision, and a swapped code would produce an empty capture that looks like a quiet market rather than a wrong route.

## The capture uses the depth feed because it is the superset

One `MODE_DEPTH` connection captures everything the touchline would send plus the five levels a side the quote endpoint also reports. Partials merge through `TickAssembler`, so the comparison sees the same merged tick the future shard will emit.

## What the synthetic checks pin in the REST half

Three checks were added so mutation testing has something to kill mutants with: `check_exchange_code_translation` pins the routing table, `check_compare_tick_to_quote` pins the comparison's counts and mismatch behaviour, and `check_implied_scale_ratio` pins the scale measurement. Two lessons shaped them. The compared-value counts are asserted exactly (15 for a full quote, 5 for a quote without depth) because a dropped comparison changes the count even when it changes no disagreement. And the median check uses three samples with a deliberate outlier because a mean would agree with a median on one or two samples — the mutant that swaps `median` for `mean` survived until the third sample existed.

## Mutation testing

Ten mutants, all killed by the thirteen-check suite: dropping the divisor in the comparison, swapping the depth sides, skipping the quantity comparison, counting absent depth levels, dropping the divisor in the scale ratio, swapping median for mean, misrouting currency to NFO, misrouting BSE indices to BFO, and both directions of the tolerance. The first mutation run had the mutants stacking on each other because the source was mutated on top of the previous mutant instead of restored from the backup each iteration; the reported survives from that run were bogus, and the run was repeated with a restore between mutants.