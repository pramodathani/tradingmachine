# data/mapping/groww.py

Ported from UBI's `back_office/instruments_v2/adapters/groww.py`, classification side only — the order, quote, and portfolio methods were not ported (data layer only). The rules file is `rules/groww.yaml`; the reasoning for each rule lives there in UBI's source and is summarized in `rules/groww.yaml.md`.

## The two pre-checks, run before the rules engine

`nse_fixed_income` is a negative-series check: an NSE cash-market row whose series is **not** one of the known equity, fund, and trust series and whose ISIN is **not** INF-prefixed is a bond. Neither half is an equality rule, which is why the segment's YAML entry has `rules: []` and the check runs here. The `series and not pd.isna(series)` guard matters: pandas represents a NULL series as NaN, NaN is truthy in Python, so a plain truthiness check misrouted blank-series rows (NSE indices among them) into fixed income before UBI caught it. Black_box's raw columns are all TEXT so NULLs arrive as None rather than NaN, but the guard is kept because it is correct for both representations.

`bse_exchange_traded_funds` requires the row's trading symbol to be in the allowlist from `known_bse_etf_symbols`, the cross-broker 2-of-N name voting set. Groww tags BSE funds and exchange traded funds alike with no internal signal to separate them, exactly like Dhan's BSE case.

## The redirects

- An `nse_equities` row with an INF-prefixed ISIN and series EQ is an exchange traded fund, redirected to `nse_exchange_traded_funds`; with any other series it is dropped into the uncategorised bucket.
- An NSE FNO futures or options row whose underlying is one of the six equity index names is redirected to the corresponding index segment. UBI needed this redirect because its own YAML listed the general FNO rule first; here the canonical order requires the general segment first anyway.
- The same redirect exists for MCX rows with the MCXBULLDEX or MCXMETLDEX underlying. In UBI this case needed **no** adapter code, because its YAML listed the index-specific commodity segments first and first-match-wins claimed the index rows. The canonical order here puts plain commodity futures and options before index futures and index options, inverting that precedence, so the redirect became necessary — see `rules/groww.yaml.md`.

## The exclusions

- `bse_equities` series B rows with a missing or INF-prefixed ISIN are dropped (they are funds; the crossref allowlist picks up the real exchange traded funds through the pre-check).
- `bse_equity_indices` drops the one blank-trading-symbol garbage row UBI found in Groww's file.
- `bse_fixed_income` drops rows with a missing or INF-prefixed ISIN, the same fund-contamination exclusion as Dhan's.

## Identity overrides

`nse_equity_indices` normalizes each symbol to uppercase alphanumerics and resolves it through the day's already-written `instruments.master` rows for `nse_equity_indices` (via the `equity_index_symbols` crossref helper), falling back to a fixed alias dict for names that do not survive normalization. This is why Groww runs after Dhan in the processing order: Dhan writes the NSE index rows first, so Groww's names converge onto Dhan's spellings and the two brokers' index ids merge. `bse_equity_indices` applies a two-entry alias dict. The three NSE fund segments strip broker-specific suffixes: "-EQ" from exchange traded funds, "-IV" from investment trusts, "-MF" from mutual funds.

## Broker field override

`bse_fixed_income` falls back to the trading symbol for `broker_symbol` when the name column is NULL, with the same NaN-awareness as the series check. UBI found that a plain falsy check missed pandas' NaN, storing the literal string "NaN" in the column.

## Uncategorised exchange

Groww's `exchange` column is a plain code (NSE/BSE/MCX), so `uncategorised_exchange` maps it directly; any other value routes to the plain `uncategorised` bucket.