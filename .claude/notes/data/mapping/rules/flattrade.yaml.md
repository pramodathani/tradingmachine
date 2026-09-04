# data/mapping/rules/flattrade.yaml

Ported from UBI's `back_office/instruments_v2/adapters/rules/flattrade.yaml`, reordered into the canonical segment order and with all collections in block style. `raw_table` points at this project's `instruments.flattrade`.

Two entries carry no rules — `nse_equities` and `nse_exchange_traded_funds` — because the NSE EQ and BE codes cover both plus a third case to exclude, and only a cross-broker allowlist separates them. `bse_equities`' rule covers just the unambiguous BSE codes; its A and B rows are split in the adapter the same way. UBI expressed the empty case as a rule matching a sentinel value that no row can carry; an empty rules list says the same thing without the sentinel.

`tick_size` points at `tick_size`, a column Flattrade's file does not have, so it resolves to nothing everywhere. That is intentional: this broker publishes no tick size at all, and naming the absent column states that plainly.

Every derivative segment names `day_month_name_year_date` for its `DD-MON-YYYY` expiry text. The BSE option segments' `strike_price` points at the `strike` column, which the adapter then corrects from the trading symbol.
