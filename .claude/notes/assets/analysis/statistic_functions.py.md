# assets/analysis/statistic_functions.py

`StatisticFunctions` holds the eight TA-Lib statistic functions from the old `Instrument`, ported on 2026-09-14 with unchanged method names and column labels. Shared background is in `price_analysis.py.md`.

## Beta and correlation against a benchmark

The old `beta` and `correlation_coefficient` compared an instrument's own `high` column with its own `low` column, so neither measured anything about the market. The port first copied this unchanged. The user asked for it to be corrected on 2026-09-14.

Both methods now take a required `benchmark` as their first argument, such as NIFTY, plus a `column` defaulting to `close`. The benchmark is typed as `PriceAnalysis`, not `Instrument`, because `assets.instruments` imports this module and importing it back would be circular; anything with a `prices` method works. This is a breaking change to the signature: an old call such as `beta(window=14)` now fails because `benchmark` is missing, which is better than silently giving the old meaningless number.

`_prices_with_benchmark` fetches both sets of candles with the same range arguments and joins them on `datetime` with an inner join. A candle that only one side has, such as a stock suspended on a day the index traded, is left out rather than filled in. The benchmark's column is kept in the frame as `benchmark_<column>`, so the caller can see what was compared.

**TA-Lib's beta argument order is the reverse of what its documentation suggests.** In TA-Lib 0.6.8, `talib.BETA(x, y)` returns the beta of `y` measured against `x`. A check on 2026-09-14 over 60 daily returns of INFY and NIFTY found:

| Calculation | Result |
|---|---|
| Hand-computed covariance of INFY and NIFTY returns divided by NIFTY's variance | 2.171 |
| `talib.BETA(index, stock)` | 2.171 |
| `talib.BETA(stock, index)` | 0.167 |

The method therefore passes the benchmark first. The result is consistent with the other figures from the same check: a correlation of 0.602, and INFY's daily moves being about 3.6 times the size of NIFTY's (standard deviations of 0.0222 and 0.0061). Beta equals correlation times that ratio. An instrument measured against itself gives 1.0.

`correlation_coefficient` correlates returns, the fractional change from one candle to the next, not price levels. Two unrelated prices that both trend upwards would otherwise show a high correlation. Beta needs no such step, because TA-Lib's `BETA` already works on changes internally. Over two years of INFY against NIFTY, the 60-candle correlation ranged from 0.093 to 0.802.

## Things carried over unchanged

- **Variance ignores its multiple.** `variance` passes `standard_deviations` to TA-Lib's `VAR` as `nbdev`, as the old code did, but TA-Lib's variance does not use it. The docstring says so.
