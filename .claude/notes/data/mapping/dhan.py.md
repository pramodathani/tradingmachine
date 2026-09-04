# data/mapping/dhan.py

Ported from `unified_broker_interface`'s `back_office/instruments_v2/adapters/dhan.py`, classification side only — UBI's order/quote/portfolio methods were not ported (data layer only). The rules file is `rules/dhan.yaml`; the reasoning for each rule lives there in UBI's source and is summarized in `rules/dhan.yaml.md`.

## The four post-filters, from UBI's live findings

- `bse_equity_indices` drops security id 846: a duplicate, unconfirmed "CAPINS" index that UBI's v1 BSE index script also dropped.
- `nse_equity_indices` drops the seven "Nifty GS ..." indices: they are government securities bond indices, belonging to `nse_fixed_income_indices`, which no broker in this build covers.
- `bse_fixed_income` / `nse_fixed_income` drop rows with a missing or INF-prefixed ISIN: fund contamination that v1 also excluded defensively. The identity for these segments is the ISIN itself, so a row without a usable one cannot be identified.
- `bse_exchange_traded_funds` requires the row's symbol to be in `known_bse_etf_symbols` (a crossref allowlist): Dhan's own MF/ETF instrument type mixes real ETFs with BSE STAR MF scheme codes and has no internal signal to separate them.

## The mutual-funds / ETF ordering interaction

UBI's dhan.yaml listed `nse_exchange_traded_funds` (rule: instrument_type MF/ETF **and** series exactly EQ) before `nse_mutual_funds` (rule: instrument_type MF/ETF, any series), so first-match-wins gave mutual_funds only the complement of the EQ rows — replicating v1's "series <> EQ" exclusion through rule precedence for free.

The canonical segment order required by this project's validation lists `mutual_funds` before `exchange_traded_funds` (both are catch-alls; mutual funds come first in the vocabulary), which inverts that precedence: the broader mutual_funds rule would claim the EQ-series ETF rows first. Rather than bend the canonical order, the adapter's `classify` redirects a mutual-fund-segment row with series EQ to the exchange traded funds segment explicitly. Same outcome, and the exclusion no longer depends on file order.

## Where BSE STAR MF scheme codes land

Dhan has no `bse_mutual_funds` segment (UBI's v1 did not either), and the BSE ETF allowlist drops scheme codes that fail the cross-reference. UBI silently discarded those rows; here they fall into `bse_uncategorised`, where they are counted and recoverable.

## Uncategorised exchange

Dhan's `exch_id` is a plain exchange code (NSE/BSE/MCX), so `uncategorised_exchange` maps it directly; any other value routes to the plain `uncategorised` bucket.