# assets/analysis/statistic_functions.py

`StatisticFunctions` holds the eight TA-Lib statistic functions from the old `Instrument`, ported on 2026-09-14 with unchanged method names and column labels. Shared background is in `price_analysis.py.md`.

Things carried over unchanged on purpose:

- **Beta and correlation use the same instrument.** `beta` and `correlation_coefficient` compare the instrument's own `high` column with its own `low` column. Beta is normally measured against a benchmark such as NIFTY, so these values are not a market beta. A benchmark version would need a second instrument's candles, and could be added later.
- **Variance ignores its multiple.** `variance` passes `standard_deviations` to TA-Lib's `VAR` as `nbdev`, as the old code did, but TA-Lib's variance does not use it. The docstring says so.
