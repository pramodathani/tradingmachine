# data/mapping/rules/dhan.yaml

Ported from UBI's `back_office/instruments_v2/adapters/rules/dhan.yaml`, reordered into the canonical segment order (fixed income, equities, currencies, commodities, catch-alls, uncategorised; within each class simple instruments, futures, options, indices, index futures, index options) and with all collections in block style. `raw_table` points at this project's `instruments.dhan`. Segment values are unchanged from UBI's (already exchange-prefixed).

## What each field means

`rules` are evaluated first-match-wins across the segments in file order against the raw row; a `match` value that is a list means "column value is one of these". `identity` and `broker_fields` map each target field to either a raw column name or a `{column, transform}` pair naming one of the transforms in `data/mapping/base.py`.

## Segment-specific reasoning carried over from UBI

- Fixed income identity is the **ISIN** (`symbol: isin`), not a ticker — India's one-off corporate bonds and NCDs have tickers that do not reconcile across brokers, while ISINs do.
- `tick_size` uses `divide_by_100` on every derivative segment (Dhan reports derivative ticks in paise-like hundredths) and the plain column on cash and index segments.
- `nse_fixed_income` is the canonical replacement for what UBI v1 miscategorized into a non-canonical `nse_corporate_bonds` table — the seven-broker bug class that config validation now makes impossible.
- The uncategorised entries at the end (nse, bse, mcx, plus plain `uncategorised` on exchange `unknown`) are this project's addition; UBI dropped unmatched rows silently.

## Ordering-dependent rules made explicit

UBI relied on `nse_exchange_traded_funds` being listed before `nse_mutual_funds` so its narrower series-EQ rule claimed those rows first. The canonical order lists mutual_funds first, so that exclusion moved into the adapter's `classify` override — see `dhan.py.md`. No other Dhan rule pair depends on listing order: every pair of rules that could match the same row differs on instrument_type or series values that are disjoint.