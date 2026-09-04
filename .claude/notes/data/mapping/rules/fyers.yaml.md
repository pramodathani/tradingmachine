# data/mapping/rules/fyers.yaml

Ported from UBI's `back_office/instruments_v2/adapters/rules/fyers.yaml`, reordered into the canonical segment order and with all collections in block style. `raw_table` points at this project's `instruments.fyers`.

## Codes are quoted

Fyers reports exchange, segment, and instrument type as numeric codes rather than names: exchange 10 is NSE, 11 is MCX, 12 is BSE; segment 10 is the cash market, 11 derivatives, 12 currency, 20 commodities. UBI's raw table stored those as integers, so its rules matched bare numbers. This project's raw tables are entirely text, so every code in this file is a quoted string and the adapter compares strings too. Matching an unquoted `10` here would silently match nothing.

## Expiry is an epoch

`expiry_date` is a Unix epoch in seconds, so every derivative segment names the `unix_epoch_date` transform. The base class refuses a numeric expiry with no transform rather than guessing the unit, which is what caught this on Fyers in the first place: pandas assumes nanoseconds for a bare number, and the raw value crashed as "year must be in 1..9999".

## Rules that never fire

The rules on the two cash-market umbrellas — every `exchange: '10', segment: '10'` entry and the BSE `exchange: '12', segment: '10'` type 0 and type 50 entries — are documentation, not live classification. The adapter routes both umbrellas entirely in code, because one instrument type code covers several segments and the split needs a ticker suffix, an ISIN check, or a cross-broker allowlist. They are kept because they record which type codes belong to which segment, which is otherwise written down nowhere.

`bse_exchange_traded_funds` and `bse_investment_trusts` carry no rules at all: both are reached only through the cross-broker allowlists.

## The one ordering inversion

UBI's file listed `nse_fixed_income_index_futures` **before** `nse_fixed_income_futures` so its narrower rule, which adds `underlying_symbol: ONMIBOR`, claimed the rate index futures first — the format has no "not equal" operator, so ordering was the only way to express the exclusion. The canonical order puts futures (rank 1) before index futures (rank 4), inverting that, so the adapter redirects an ONMIBOR row out of `nse_fixed_income_futures` instead.

## broker_symbol on this broker

Most segments carry `symbol_details`, which is a human-readable description such as "RELIANCE 29 Sep 26 FUT" rather than a tradeable ticker. The derivative segments that could carry a real ticker use `symbol_ticker` with `strip_exchange_prefix`. Neither is a substitute for the symbol format Fyers' order and quote endpoints expect; see `fyers.py.md`.
