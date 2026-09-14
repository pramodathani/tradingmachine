# assets/analysis/momentum_indicators.py

`MomentumIndicators` holds the 28 TA-Lib momentum indicators from the old `Instrument`, ported on 2026-09-14. Shared background and the shared parameter renames are in `price_analysis.py.md`.

The one method rename is `williams_percent_R` to `williams_percent_r`, because method names are lower case.

## The stochastic RSI's period, corrected

The old `stochastic_relative_strength_index` passed `fast_k_period`, default 5, to TA-Lib's `timeperiod`, which is the length of the underlying RSI, and left TA-Lib's own `fastk_period` at its default. The result was a stochastic of a 5-candle RSI, which differs from the usual 14-candle stochastic RSI in charting tools.

The port first copied this unchanged. The user asked for it to be corrected on 2026-09-14. The method now takes a separate `window`, default 14, for the RSI length and passes `fast_k_period` to TA-Lib's `fastk_period`. With its defaults it matches `talib.STOCHRSI` with TA-Lib's own defaults of 14, 5 and 3; this was checked on INFY candles. The output labels `stochrsi_fastk<period>` and `stochrsi_fastd<period>` did not change, but the values under them did.

## Things carried over unchanged

The port copies behaviour rather than silently fixing it, so these remain:

- **Two MACD labels.** `moving_average_convergence_divergence` labels its columns `macd_<fast>_<slow>_<signal>`, `..._signal` and `..._hist`. `moving_average_convergence_divergence_extended` uses `macd_<suffix>`, `macd_signal_<suffix>` and `macd_hist_<suffix>`. The two therefore produce differently named signal and histogram columns.
- **Labels without an underscore.** `ppo<fast>_<slow>`, `stochf_fastk<period>`, `stochf_fastd<period>`, `stochrsi_fastk<period>` and `stochrsi_fastd<period>` lack the underscore that other labels have.
- **Differing default windows.** `average_directional_movement_index_rating` and `directional_movement_index` default to 10 candles, while `average_directional_movement_index` defaults to 14.
- **Unclear names in the ultimate oscillator.** `ultimate_oscillator` calls its three windows `fast_period`, `slow_period` and `signal_period`, as the old code did, although they are the short, middle and long windows.

All 28 methods ran without error against 270 INFY daily candles on 2026-09-14.
