# data/mapping/wisdom_capital.py

Ported from UBI's `back_office/instruments_v2/adapters/wisdom_capital.py`, classification side only. The rules file is `rules/wisdom_capital.yaml`.

## The redirect table, and why it exists

Wisdom Capital reports instrument type as a numeric code — 1 for futures, 2 for options, 16 for underlying references — and one code plus exchange segment covers several of this project's segments at once. UBI separated them purely by listing order: the narrow name-list segment came first, so first-match-wins left the general segment only the remainder.

The canonical segment order lists the general segment first in **every one** of those pairs, which inverts the whole scheme. Rather than scatter a dozen conditionals through `classify`, the separations are stated once as `NAME_REDIRECTS`, a table of (matched segment, underlying names, target segment) triples applied in a single loop. The twelve entries cover index derivatives on NSE, BSE, and MCX; the MCX index spot rows; the currency derivatives that share the rate derivative code on both exchanges; and the overnight rate index futures.

This is the largest instance of the ordering inversion that reordering into the canonical order caused across the whole build, and it is the reason the redirect table is worth having as data rather than as code.

## The series duplicate

A cash-market symbol can be listed twice under two different series at once, for example EQ and T0. `read_raw_rows` sorts the day's rows worst-series-first so the preferred series is written last and survives the collapse onto one instrument id. UBI achieved the same with a dedicated dedup pass inside a duplicated `run`; using the base class's read hook keeps one `run` for every broker.

## The BSE cash market

BSE rows carry no native fund, trust, or bond marker at all. The order of checks matters and is fixed in code: the cross-broker fund allowlist, then the trust allowlist, then the F and G series with a real ISIN, then — after dropping the duplicate rows whose name ends in a hash — the clean series list, and finally the B series when its ISIN is not a fund ISIN.

## The two-source fixed income segment

`nse_fixed_income` merges two disjoint raw shapes: NSE cash bonds, identified by ISIN, and the currency-segment rate derivative underlying references, identified by name and carrying no real lot or tick size. `to_identity` and `to_broker_fields` both branch on the raw exchange segment for that reason.

## Small corrections

Option types are the numeric codes 3 and 4, remapped to CE and PE for every option-shaped segment. The BSE rate futures segments carry placeholder rows that are not real contracts, dropped by matching the description against a single-leg contract pattern. Three BSE index names are aliased onto the canonical spelling, and one literal test row in the NSE commodity segment is dropped by name.

## Verified counts

On the 2026-09-04 snapshot this adapter classified 205,216 of 209,385 raw rows, leaving 4,169 uncategorised and no errors.
