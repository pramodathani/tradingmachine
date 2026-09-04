# data/instruments/dhan.py

Dhan publishes one public CSV, the detailed scrip master, covering every exchange. Thirty-two real columns.

Every line ends with a trailing comma, so pandas creates a thirty-third `Unnamed: 32` column that is empty on every row. The base class drops it, having first confirmed it holds nothing.

The natural key is exchange, segment and security identifier together, because the security identifier alone repeats across segments. Sorting by series first keeps the surviving row predictable when the same instrument appears more than once.

Verified on 2026-09-04: 199,540 rows after dropping the artifact column, no duplicates.
