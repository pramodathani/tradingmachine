# src/tradingmachine/assets/analysis/strategy_backtests.py

`StrategyBacktests` holds `run_backtest` from the old `Instrument`, ported on 2026-09-14. It uses the `backtesting` package (version 0.6.5).

The old method dropped the `exchange`, `segment` and `interval` columns and assumed the five that remained were the candle columns. UBI's candles now also carry `oi`, and `price_factor` when adjusted, so the method selects `open`, `high`, `low`, `close` and `volume` by name before renaming them to the capitalised names `backtesting` requires.

## Plotting is optional

The old method always called `backtest.plot()`. `backtesting` then wrote an HTML file named after the strategy into the current working directory and opened it in a browser. Running from the project root left a stray file there, and every backtest opened a browser tab.

The user asked for this to change on 2026-09-14. `run_backtest` now takes `plot_filename`, which defaults to None:

- With None, no plot is drawn and no file is written.
- With a path, the plot is written to that file with `open_browser=False`, so nothing opens by itself. `results=statistics` is passed so the plot shows the run just made rather than running the strategy again.

A check on 2026-09-14 confirmed that a run without a filename wrote no HTML file. A run with `plot_filename="sma_cross.html"` wrote an 82,745-byte file and reported the same 9 trades.

The candles' `datetime` index is in India time with a time zone attached, and `backtesting` accepted it. On 2026-09-14, a 10 and 30 candle SMA crossover strategy over 730 days of INFY ran and reported 9 trades.
