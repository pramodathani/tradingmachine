# data/instruments/groww.py

Groww publishes one public CSV covering every exchange and segment, twenty-one columns.

The natural key is exchange, segment and trading symbol together. Groww's `exchange_token` is not unique across segments, so the trading symbol is what actually distinguishes rows.

Verified on 2026-09-04: 134,335 rows after dropping 2 duplicates.
