# src/tradingmachine/assets/analysis/signals.py

`Signals` holds `is_cross_over` and `is_cross_under` from the old `Instrument`, ported on 2026-09-14. They work on a frame the caller passes in and do not fetch candles.

## The crossover test, corrected

The old `is_cross_over` marked a row when the previous row's first column was at or below the current row's second column, and the current second column was below the current first column. That compares the previous first value against the current second value. The usual test compares the two columns on the previous row, then the two columns on this row. The two agree when the second column changes slowly, such as a moving average, and can disagree when it moves sharply.

The port first copied the old test. The user asked for the textbook version on 2026-09-14:

| Method | Previous row | This row |
|---|---|---|
| `is_cross_over` | first column at or below second | first column above second |
| `is_cross_under` | first column at or above second | first column below second |

On 400 days of INFY closes against a 20-candle simple moving average, the new methods marked 16 crossovers and 17 crossunders. Both matched a separate hand-written version of the textbook test on every row. The first row is never marked, because it has no previous row.

## Other changes from the old code

The old methods added a helper column named `shifted_column1`, then narrowed the frame back to its original columns to hide it. The new methods keep the shifted values in local variables, so no helper column is ever added. `reset_index(drop=True)` returns a new frame, so the caller's frame is not changed; the check confirmed the input frame gained no column.

The methods do not use the instrument's state. They stay instance methods, as in the old code, so they are called the same way as every other analysis method.
