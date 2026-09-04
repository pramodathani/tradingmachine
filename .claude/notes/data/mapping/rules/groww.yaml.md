# data/mapping/rules/groww.yaml

Ported from UBI's `back_office/instruments_v2/adapters/rules/groww.yaml`, reordered into the canonical segment order and with all collections in block style. `raw_table` points at this project's `instruments.groww`. UBI's version carried long explanatory comments; that content lives here and in `groww.py.md` instead.

## The three rules-free segments

`nse_fixed_income`, `nse_exchange_traded_funds`, and `bse_exchange_traded_funds` have `rules: []`. None of their conditions is expressible as an equality match: fixed income is a negative-series-plus-ISIN check, and both exchange traded fund segments are reached only through redirects and the crossref allowlist inside `groww.py`. Their entries exist so the adapter has an identity and broker field mapping to key off of, and so config validation accepts the segment.

## Rules that never fire through the engine

The `nse_equity_index_futures`, `nse_equity_index_options`, `mcx_commodity_index_futures`, and `mcx_commodity_index_options` rules carry underlying lists, but they are listed after the general futures and options segments in the canonical order, so first-match-wins means the general rules claim those rows first and the adapter's redirect moves them. The underlying lists are kept from UBI's file as documentation of exactly which underlyings count as index derivatives; the redirect in `groww.py` is the operative mechanism.

## Where the canonical order inverted UBI's tricks

UBI's groww.yaml listed `mcx_commodity_index_futures` and `mcx_commodity_index_options` **before** the general `mcx_commodity_futures` and `mcx_commodity_options`, so the index-specific rules claimed the MCXBULLDEX and MCXMETLDEX rows first with no adapter code at all. The canonical order required here puts plain futures and options before index futures and index options within the commodities class, which inverts that precedence. The adapter's `classify` override redirects MCX rows with an index underlying from the general segment to the index segment, the same pattern the Dhan adapter uses for its mutual funds and exchange traded funds ordering interaction. The NSE equity futures and options pair needed the same redirect in UBI already, because UBI's own file listed the general NSE FNO rules first.

## Segment-specific reasoning carried over from UBI

- Fixed income identity is the **ISIN** (`symbol: isin`), not a ticker, for both exchanges — the same reasoning as Dhan's fixed income entries.
- `bse_equities` carries two rules: the main series list, and series `B` as its own rule, because series B rows are the ones the adapter splits into equity and exchange traded fund by ISIN prefix.
- `nse_commodity_futures` and `nse_commodity_options` use `divide_by_100` on tick size; every other Groww segment uses the plain column, since Groww's own values are already plain.
- The uncategorised entries at the end (nse, bse, mcx, plus plain `uncategorised` on exchange `unknown`) are this project's addition; UBI dropped unmatched rows silently.