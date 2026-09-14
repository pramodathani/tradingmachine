# assets/analysis/momentum_indicators.py

`MomentumIndicators` holds the 28 TA-Lib momentum indicators from the old `Instrument`, ported on 2026-09-14. Shared background and the shared parameter renames are in `price_analysis.py.md`.

The one method rename is `williams_percent_R` to `williams_percent_r`, because method names are lower case.

Things carried over unchanged on purpose, because the port copies behaviour rather than silently fixing it:

- **The stochastic RSI's period.** `stochastic_relative_strength_index` passes `fast_k_period`, default 5, to TA-Lib's `timeperiod`, which is the length of the underlying RSI. TA-Lib's own `fastk_period` is left at its default of 5. The usual stochastic RSI uses a 14-candle RSI, so results differ from most charting tools.
- **Two MACD labels.** `moving_average_convergence_divergence` labels its columns `macd_<fast>_<slow>_<signal>`, `..._signal` and `..._hist`. `moving_average_convergence_divergence_extended` uses `macd_<suffix>`, `macd_signal_<suffix>` and `macd_hist_<suffix>`. The two therefore produce differently named signal and histogram columns.
- **Labels without an underscore.** `ppo<fast>_<slow>`, `stochf_fastk<period>`, `stochf_fastd<period>`, `stochrsi_fastk<period>` and `stochrsi_fastd<period>` lack the underscore that other labels have.
- **Differing default windows.** `average_directional_movement_index_rating` and `directional_movement_index` default to 10 candles, while `average_directional_movement_index` defaults to 14.
- **Unclear names in the ultimate oscillator.** `ultimate_oscillator` calls its three windows `fast_period`, `slow_period` and `signal_period`, as the old code did, although they are the short, middle and long windows.

All 28 methods ran without error against 270 INFY daily candles on 2026-09-14.
