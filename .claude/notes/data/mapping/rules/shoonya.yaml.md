# data/mapping/rules/shoonya.yaml

Ported from UBI's `back_office/instruments_v2/adapters/rules/shoonya.yaml`, reordered into the canonical segment order and with all collections in block style. `raw_table` points at this project's `instruments.shoonya`.

Shoonya's raw columns are close to a clean vocabulary — one `exchange` code and one `instrument` code per row — so most segments are a plain two-column match. Two entries carry no rules: `nse_fixed_income`, whose condition is a code list plus a blank-or-prefixed test, and `nse_exchange_traded_funds`, which is a cross-broker allowlist. Both are reached from `shoonya.py`.

The BSE derivative segments deliberately point their `underlying_symbol` at `tradingsymbol`, which the adapter then re-extracts by pattern; the `symbol` column those rows carry is stale and does not track renames.

Every derivative segment names the `day_month_name_year_date` transform for expiry, since Shoonya ships `DD-MON-YYYY` text.

No rule pair in this file depends on listing order: the two conditions that could collide with a rule — the fund allowlists and the bond test — are both checked in the adapter before the rules engine runs.
