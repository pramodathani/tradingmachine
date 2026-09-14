# assets/analysis/strategy_backtests.py

`StrategyBacktests` holds `run_backtest` from the old `Instrument`, ported on 2026-09-14. It uses the `backtesting` package (version 0.6.5).

The old method dropped the `exchange`, `segment` and `interval` columns and assumed the five that remained were the candle columns. UBI's candles now also carry `oi`, and `price_factor` when adjusted, so the method selects `open`, `high`, `low`, `close` and `volume` by name before renaming them to the capitalised names `backtesting` requires.

`backtest.plot()` is still called, as before. `backtesting` writes the plot as an HTML file named after the strategy in the current working directory, and opens it in a browser. Running from the project root therefore leaves an HTML file there. A `plot` argument could make this optional if it becomes a nuisance.

The candles' `datetime` index is in India time with a time zone attached, and `backtesting` accepted it. On 2026-09-14, a 10 and 30 candle SMA crossover strategy over 730 days of INFY ran and reported 9 trades.
