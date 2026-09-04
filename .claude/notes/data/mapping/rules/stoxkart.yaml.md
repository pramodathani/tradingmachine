# data/mapping/rules/stoxkart.yaml

Ported from UBI's `back_office/instruments_v2/adapters/rules/stoxkart.yaml`, reordered into the canonical segment order and with all collections in block style. `raw_table` points at this project's `instruments.stoxkart`. This is the largest rules file in the project: 39 real segments plus the four per-exchange uncategorised buckets and the plain one.

## Why so many segments have no rules

Fifteen entries carry `rules: []`. Stoxkart is the only broker whose file mixes calendar spreads, reference rows, and real contracts inside one instrument type, and whose raw file lists the same instrument two or three times. Those conditions are winner sets, regular expressions, and cross-broker allowlists, none of which the equality rule engine can express, so the segments are reached from `stoxkart.py` instead. Their entries still carry the identity and broker field mapping, and still satisfy config validation.

## Expiry dates

Stoxkart ships `expiry_date` as `DD-MM-YYYY` text on **every** date-bearing segment, not only the derivatives. Each such segment therefore names the `day_month_year_date` transform explicitly. Without it the generic parser reads any day of 12 or less as a month, which silently mis-dates roughly a third of every expiry.

## The two scaling families

Value scaling is not uniform across this broker's own segments, so it is expressed per segment rather than per broker:

- `divide_by_100` on the equity family derivatives, the exchange traded funds, the investment trusts, and the MCX and NCDEX commodity option strikes.
- `divide_by_10_million` on every currency and fixed income derivative segment, for both strike price and tick size. UBI applied this one in Python because adding a transform to its registry was out of scope for that fork; here it is a named transform, so the YAML says what happens.

The segments whose lot and tick values are meaningless (`nse_currencies`, `bse_currencies`, and the two fixed income index segments, plus the NSECD half of `nse_fixed_income`) are forced to NULL in the adapter, since the rules schema has no way to say "no value".

## Ordering

No rule pair in this file depends on listing order. Every case where two segments could claim the same row is settled in `stoxkart.py`: either in the early checks, which run before the rules engine, or in the post-filter, which redirects rather than dropping. That is why reordering UBI's file into the canonical order changed no outcome here, unlike Dhan and Groww.
