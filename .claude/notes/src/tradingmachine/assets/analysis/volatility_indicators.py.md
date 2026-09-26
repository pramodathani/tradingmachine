# src/tradingmachine/assets/analysis/volatility_indicators.py

`VolatilityIndicators` holds the three TA-Lib volatility indicators from the old `Instrument`, ported on 2026-09-14 with unchanged names. Shared background is in `price_analysis.py.md`.

The column labels are unchanged, including `natr<window>`, which lacks the underscore that `atr_<window>` has.

## The `natr<window>` column name, noted on 2026-09-26

`normalized_average_true_range` names its column `natr14`, without the underscore every other method uses (`atr_14`, `rsi_14`). It was left as it is when instruments_explorer started reading it, because renaming the column would change the frames the method returns for every existing caller. instruments_explorer reads `natr<window>` accordingly.
