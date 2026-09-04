# data/mapping/zerodha.py

Ported from UBI's `back_office/instruments_v2/adapters/zerodha.py`, classification side only. The rules file is `rules/zerodha.yaml`, which carries no rules at all.

## Why classification is entirely in code

Zerodha publishes one flat instrument type per exchange with no discriminating column. NSE "EQ" covers equities, exchange traded funds, mutual fund plans, investment trusts, and corporate bonds together. BSE "EQ" covers the same minus mutual funds. The currency segment covers currency pairs, government bond derivatives, and the overnight rate index together. The derivative exchanges mix stock and index contracts.

Nothing in that is an equality match, so `classify` dispatches on exchange, segment, and instrument type together and every segment's rules list is empty. The rules file still earns its place: it holds the identity and broker field mappings, which the base class reads for whichever segment the dispatch picks.

## The NSE suffix rule, and the bug in the obvious version

The NSE flat bucket is decided by the trading symbol's suffix. The suffix is the **last** hyphen-separated part, not the second: a base symbol can itself contain a hyphen, so "NXT-INFRA-IV" splits into three parts and the second one is "INFRA", not the real suffix "IV". Taking the second part misfiles every such row.

Bond tranche suffixes win first, then the trust and mutual fund suffixes — checked before the blank-name drop, because this broker's mutual fund rows have a blank name on every single row.

## The BSE heuristics, and their order

The BSE flat bucket has no suffix convention, so it is a sequence of name and symbol heuristics. The cross-broker fund allowlist is checked **first** and deliberately: one of the bond heuristics is "blank name and any digit in the symbol", which is broad enough to claim a fund ticker such as "GSEC10ADD" if it ran first.

## Dual membership

`classify_extra` re-checks the equity criteria on every BSE flat row independently of what the primary dispatch chose. These segments were originally separate, non-exclusive queries, and a substantial minority of the rows whose name equals their trading symbol — one of the bond heuristics — are also genuinely equities. Re-checking restores that second membership rather than losing it. Because it is a genuine re-check rather than a correction, it is harmlessly redundant on rows the dispatch already sent to equities.

This is why Zerodha's run reports more segment memberships than raw rows: on the 2026-09-04 snapshot, 108,317 classified rows and 495 uncategorised — together exactly the 108,812 raw rows — producing 113,543 memberships.

## No ISIN

Zerodha carries no ISIN column, so both fixed income segments resolve their identity through the shared security identifier map, keyed on this broker's `exchange_token`, which sits in the same exchange-assigned numbering the ISIN-bearing brokers use.

An unresolvable row is left for the uncategorised bucket, the same as Shoonya. An earlier version raised instead, on the reasoning that the map is expected to cover this broker completely and that a gap deserved to be loud. That reasoning was wrong, and a real date proved it: on 2026-08-12 only Zerodha was downloaded, so the map — which pools other brokers' files for the same date — was empty, and 13,896 bond rows raised. A raise means the row is never written at all, so those instruments simply vanished from that date and the run's own coverage stopped reconciling. Being loud is not worth breaking the invariant that every raw row is either classified or filed somewhere countable. The check now sits in `classify`, before an identity is attempted, and that date maps with 99,827 classified, 14,571 uncategorised, and no errors.
