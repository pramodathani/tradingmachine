# data/instruments/zerodha.py

Zerodha publishes one public CSV at `https://api.kite.trade/instruments` covering every exchange it supports. No authentication, no query parameters, twelve columns.

The instrument token is unique across the whole dump by Kite Connect's own design, so it is the natural key on its own and no sort column is needed to make de-duplication predictable.

Verified on 2026-09-04: 108,812 rows, no duplicates, no artifact columns.
