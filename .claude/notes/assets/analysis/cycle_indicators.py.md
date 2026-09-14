# assets/analysis/cycle_indicators.py

`CycleIndicators` holds the six Hilbert transform methods from the old `Instrument`, ported on 2026-09-14 with unchanged names and column labels. Shared background is in `price_analysis.py.md`.

The Hilbert transform functions need a long warm-up before their first value. TA-Lib 0.6.8 reports a lookback of 32 candles for `HT_DCPERIOD` and `HT_PHASOR`, and 63 for `HT_DCPHASE`, `HT_SINE`, `HT_TRENDMODE` and `HT_TRENDLINE`. A short range therefore returns columns that are mostly or entirely empty. All six methods returned values over 270 INFY daily candles on 2026-09-14.
