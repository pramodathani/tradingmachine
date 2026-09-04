# data/mapping/rules/indmoney.yaml

Ported from UBI's `back_office/instruments_v2/adapters/rules/indmoney.yaml`, reordered into the canonical segment order and with all collections in block style. `raw_table` points at this project's `instruments.indmoney`.

## What the segment column actually holds

IND Money's `segment` column is not a segment vocabulary. It holds `E` for the cash market, `D` for derivatives, and for an index row it holds the **index's own name**, such as "NIFTY 50" or "S&P BSE SENSEX 50". That is why both index segments carry no rules and are classified by exclusion in the adapter, and why their identity and broker symbol both read the `segment` column.

## Expiry is month-first

`expiry_date` is `MM/DD/YYYY HH:MM` on both exchanges' derivatives — verified on the 2026-09-04 snapshot, where NIFTY-Sep2026-FUT carries 09/29/2026 14:00 and no row has a first component above 12 while 78,323 have a second one above 12. It is parsed by the adapter's own `month_day_year_time` transform. UBI applied its equivalent to the BSE side only.

## The two underlying extractions

Neither derivative segment has an underlying symbol column. The NSE segments carry `trading_symbol` as a placeholder identity and the adapter re-derives the underlying with a pattern; the BSE segments use the simpler `underlying_before_first_hyphen` transform, because BSE derivative symbols put the underlying first and never contain a hyphen inside it.

## The rules-free segments

`nse_fixed_income`, `bse_fixed_income`, both index segments, and both exchange traded fund segments carry no rules: they are instrument-type and series conditions combined with an ISIN check, an exclusion, or a cross-broker allowlist, none of which the rule engine expresses.
