# assets/analysis/overlap_studies.py

`OverlapStudies` holds the twelve TA-Lib overlap studies from the old `Instrument`, ported on 2026-09-14. Shared background is in `price_analysis.py.md`.

Method names are unchanged. Parameter renames specific to this module:

| Method | Old parameter | New parameter |
|---|---|---|
| `bollinger_bands` | `std_dev_up`, `std_dev_down` | `standard_deviations_up`, `standard_deviations_down` |
| `triple_exponential_moving_average` | `vfactor` | `volume_factor` |
| `mesa_adaptive_moving_average` | `fastlimit`, `slowlimit` | `fast_limit`, `slow_limit` |

Things carried over unchanged on purpose:

- `triple_exponential_moving_average` calls `talib.T3`, Tillson's T3, not `talib.TEMA`, which is the indicator usually called the triple exponential moving average. Its column is `t3_<window>`. The old name was kept so existing habits still work; a real TEMA method could be added beside it.
- `bollinger_bands` unpacks TA-Lib's three results into named locals before assigning columns, instead of the old tuple assignment across three subscripts, which is easier to read. The labels `bb_upper_<window>`, `bb_middle_<window>` and `bb_lower_<window>` are unchanged.

The old docstring of `mesa_adaptive_moving_average` described a `window` argument the method never had; the new docstring describes the real limits.
