# Performance measures

The performance measures are the numbers used to judge an investment over a period: how much it returned, how bumpy the ride was, how far it fell, and how it did against a benchmark. They are methods on every instrument and on every [asset basket](../python-api/asset-baskets.md), because both supply `prices`, and they live in `src/tradingmachine/assets/analysis/performance_measures.py`.

Each method takes the usual range arguments, `interval`, `from_date`, `to_date`, `days` and `adjusted`, and works on the closing prices. A return is the fractional change of the close from one candle to the next. Annual figures scale by 252 candles a year for `day` candles, and by the number of candles in 252 sessions of 375 minutes for a minute interval such as `5minute`. A `risk_free_rate` is an annual fraction, so a 6.5 percent treasury bill is `0.065`.

The table below lists the measures.

| Method | What it means | A good value |
|---|---|---|
| `cumulative_return` | Total growth over the range | Higher |
| `annualised_return` | The compound annual growth rate | Higher |
| `annualised_volatility` | The standard deviation of returns, scaled to a year | Lower, for the same return |
| `sharpe_ratio(risk_free_rate)` | Annual return above the risk-free rate for each unit of volatility | Above 1 is usually thought good |
| `sortino_ratio(risk_free_rate)` | The Sharpe ratio with only the falls counted as risk | Higher |
| `drawdowns` | How far below its earlier peak the close stood at every candle | A DataFrame, not a single number |
| `maximum_drawdown` | The worst fall from a peak, as a negative fraction | Closer to zero |
| `calmar_ratio` | Annual growth rate divided by the size of the worst drawdown | Higher |
| `value_at_risk(confidence, method)` | The one-candle loss not exceeded on that share of candles, `historical` or `parametric` | Lower |
| `expected_shortfall(confidence)` | The average loss on the candles beyond the value at risk | Lower |
| `benchmark_beta(benchmark)` | How much the price moved for each percent the benchmark moved | 1 moves with the market |
| `alpha(benchmark, risk_free_rate)` | Annual return beyond what the beta explains, Jensen's alpha | Positive |
| `tracking_error(benchmark)` | Annual volatility of the return difference from the benchmark | Near zero for an index fund |
| `information_ratio(benchmark)` | Annual return above the benchmark for each unit of tracking error | Higher |
| `up_capture_ratio(benchmark)`, `down_capture_ratio(benchmark)` | How much of the benchmark's rises and falls were captured | Up above 1, down below 1 |
| `performance_summary(benchmark=None, ...)` | Every measure above from one fetch of the candles | A pandas Series |

A benchmark is anything with a `prices` method, so an instrument can be measured against an index, a basket against the index it copies, or one fund's holdings against another's.

## Example

The example below measures INFY against NIFTY over a year. The output is real, from 2026-09-28, and the Sharpe ratio and maximum drawdown match a separate calculation with pandas to every printed digit.

=== "Python"

    ```python
    from tradingmachine.assets import equities

    infosys = equities.Equity(exchange="nse", symbol="INFY")
    nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
    print(infosys.performance_summary(benchmark=nifty, risk_free_rate=0.065, days=365))
    ```

=== "Output"

    ```
    cumulative_return       -0.306284
    annualised_return       -0.313494
    annualised_volatility     0.30328
    sharpe_ratio            -1.302082
    sortino_ratio           -1.747486
    maximum_drawdown        -0.416913
    calmar_ratio            -0.751941
    value_at_risk            0.030875
    expected_shortfall       0.045884
    benchmark_beta           0.684382
    alpha                    -0.31252
    tracking_error             0.2921
    information_ratio       -0.939854
    up_capture_ratio         0.596877
    down_capture_ratio       0.963832
    dtype: object
    ```

A mutual fund returns None for every measure, because UBI stores no candles or net asset value for one; measure its [constituents](../python-api/asset-baskets.md#an-index-or-a-fund-is-two-things) instead.
