# assets/analysis/signals.py

`Signals` holds `is_cross_over` and `is_cross_under` from the old `Instrument`, ported on 2026-09-14. They work on a frame the caller passes in and do not fetch candles.

The comparison is carried over unchanged, and it is not the textbook crossover test. `is_cross_over` marks a row when the previous row's first column is at or below the current row's second column, and the current second column is below the current first column. The usual test compares the previous first column with the previous second column. The two agree when the second column changes slowly, such as a moving average, and can disagree when it moves sharply. `is_cross_under` mirrors this. Switching to the usual test would change which rows are marked, so it should be the user's decision.

The helper column `shifted_column1` keeps its old name, because it is never returned: the result is narrowed back to the frame's original columns plus `cross_over` or `cross_under`.

The methods do not use the instrument's state. They stay instance methods, as in the old code, so they are called the same way as every other analysis method.

On 2026-09-14, `is_cross_over(frame, "close", "sma_20")` over 270 INFY daily candles marked 18 rows.
