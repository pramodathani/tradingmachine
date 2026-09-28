# src/tradingmachine/assets/analysis/performance_measures.py

`PerformanceMeasures` was added on 2026-09-28 with the asset baskets. It holds the measures people use to judge a portfolio: Sharpe, Sortino and Calmar ratios, drawdowns, value at risk, expected shortfall, and the benchmark measures beta, alpha, tracking error, information ratio and capture ratios. Nothing like it existed before; a grep for drawdown or Sharpe found nothing in the package.

## Why it is an analysis class rather than a basket feature

The measures apply equally to one share, an index, a fund or a whole basket, and they only need `prices`. So they sit beside the other analysis classes, and both `Instrument` and `AssetBasket` inherit them. That is what lets `nifty.sharpe_ratio(...)` and `nifty.constituents.sharpe_ratio(...)` be the same method working on different candles, which answered the user's question of how index, mutual fund and ETF classes get portfolio measures.

## Annualising

UBI serves only `day` candles and minute candles from `1minute` to `240minute`; there is no weekly or monthly interval, so the plan's 52 and 12 periods a year were dropped. `day` scales by 252 trading days. A minute interval scales by 252 sessions of 375 minutes divided by the candle length, the NSE's 09:15 to 15:30 session. Any other interval raises `ValueError` before any request is sent.

## Conventions chosen

- The Sharpe and Sortino ratios use the arithmetic mean return times the periods a year, the textbook form, rather than the compound growth rate `annualised_return` gives. Both are standard; the arithmetic form is what most references and libraries print.
- `maximum_drawdown` is returned as a negative fraction, matching the `drawdown` column, and `calmar_ratio` divides by its absolute value.
- `value_at_risk` and `expected_shortfall` are returned as positive loss fractions, which is how the numbers are quoted in practice.
- The parametric value at risk uses `statistics.NormalDist` from the standard library, so no SciPy dependency was added.
- The capture ratios use the plain mean of the returns on the candles where the benchmark rose, or fell, rather than a compounded version. It is the simplest form to read and check.
- `risk_free_rate` defaults to 0.0 rather than a guessed treasury bill rate, because a baked-in rate goes stale; the docstrings show 0.065 as an example.

## Why it does not reuse `StatisticFunctions._prices_with_benchmark`

`PerformanceMeasures` must work on its own, and `_prices_with_benchmark` belongs to another mixin. It has its own `_matched_returns`, which does the same inner join on `datetime` and then works out both return series. `benchmark_beta` is a single number over the whole range, which is different from the existing `beta`, a rolling TA-Lib column; the name was chosen so the two do not clash.

## One fetch per call, and one for the summary

Every public method fetches its candles once and hands the closes to a private `_..._of` helper. `performance_summary` fetches once and calls every helper, so it costs one request for the instrument and one for the benchmark rather than fifteen.

## Verified on 2026-09-28

INFY against NIFTY over 365 days gave a Sharpe ratio of -1.302082 and a maximum drawdown of -0.416913, identical to a separate pandas calculation. NIFTY's own Sharpe ratio came out at -0.8959.
