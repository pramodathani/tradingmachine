# src/tradingmachine/assets/analysis/candlestick_patterns.py

`CandlestickPatterns` holds the 61 TA-Lib candlestick pattern recognisers from the old `Instrument`, ported on 2026-09-14. Shared background is in `price_analysis.py.md`.

Each method adds one column that TA-Lib fills with 100 for a bullish match, -100 for a bearish match and 0 otherwise. `candle_hikkake` also reports 200 or -200 when a hikkake is confirmed, seen over ten years of INFY candles on 2026-09-14; the docstrings describe the common case.

Two method names were corrected to separate their words. Their column labels are unchanged, so existing code reading the frame still works:

| Old method | New method | Column label (unchanged) |
|---|---|---|
| `candle_hangingman` | `candle_hanging_man` | `candle_hangingman` |
| `candle_evening_dojistar` | `candle_evening_doji_star` | `candle_evening_dojistar` |

One mismatch is carried over: `candle_up_side_down_side_gap_three_methods` writes the label `candle_up_side_gap_three_methods`, which drops "down_side".

Some method names do not match TA-Lib's function names. For example, `candle_side_by_side_white_lines` calls `CDLGAPSIDESIDEWHITE`, and `candle_morning_star_doji` calls `CDLMORNINGDOJISTAR`. The docstrings name the pattern TA-Lib actually recognises.

All 61 methods ran without error against 270 INFY daily candles on 2026-09-14.
