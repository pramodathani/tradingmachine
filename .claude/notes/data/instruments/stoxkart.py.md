# data/instruments/stoxkart.py

Stoxkart publishes one public CSV at `https://openapi.stoxkart.com/scrip-master/csv`, thirteen columns and roughly thirty-six megabytes, which makes it the largest single file of the ten and the slowest broker to fetch.

The natural key is exchange and token together.

Verified on 2026-09-04: 464,383 rows, the largest of any broker, no duplicates.
