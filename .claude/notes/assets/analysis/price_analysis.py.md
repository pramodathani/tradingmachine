# assets/analysis/price_analysis.py

`PriceAnalysis` is the shallow base of the thirteen analysis classes in `assets/analysis/`. It declares `prices`, the one method every analysis method calls, and raises `NotImplementedError` from it, so each analysis module documents what it relies on without importing `assets.instruments`.

## Why the analysis methods are split out of Instrument

In the old project, `Instrument` held about 190 analysis methods directly, in one 3,085-line file. When the port was planned on 2026-09-14, the user chose to port every one of them, grouped into classes in separate files that `Instrument` inherits. The groups follow TA-Lib's own function groups, with tradingmachine's statistics, signals and backtest as three more:

```
PriceAnalysis                    prices() contract
  ├── PriceStatistics            39  price_*, volumes, volume_*, returns, returns_*
  ├── OverlapStudies             12  moving averages, Bollinger bands, SAR, midpoint
  ├── MomentumIndicators         28  MACD, ADX, RSI, stochastics, oscillators
  ├── VolumeIndicators            3  Chaikin A/D, OBV
  ├── CycleIndicators             6  Hilbert transform family
  ├── PriceTransforms             4  average, median, typical price, weighted close
  ├── VolatilityIndicators        3  ATR, NATR, true range
  ├── StatisticFunctions          8  beta, correlation, linear regression, deviation
  ├── MathTransforms             15  trigonometric, logarithmic, rounding
  ├── MathOperators              10  add, subtract, multiply, divide, rolling extremes
  ├── CandlestickPatterns        61  candle_*
  ├── Signals                     2  is_cross_over, is_cross_under
  └── StrategyBacktests           1  run_backtest
          ▲ all inherited by
      assets.instruments.Instrument  (supplies the real prices())
```

The user also chose to keep the old shape, in which analysis methods live on the instrument and each fetches its own candles, rather than a separate candles object. UBI is local and caches, so repeated fetches are cheap.

## Explicit price arguments

Old analysis methods took `**prices_kwargs` and passed them to `prices`. Each method now names `interval`, `from_date`, `to_date`, `days` and `adjusted` explicitly and documents them. This makes every argument visible in the signature and the docstring, as the user's style rules ask, at the cost of repetition.

## How the generated modules were written

The eleven modules built from one repeated shape (every analysis module except `signals.py` and `strategy_backtests.py`) were produced on 2026-09-14 by a one-off generator script in the session scratchpad. It rendered each method from a table of name, summary, parameters, TA-Lib call and output column, so the docstrings and signatures are uniform. The generator is not kept in the repository; the files are ordinary source and are edited by hand from now on. `ruff format` was run over the output.

## Renames that apply everywhere

Identifiers were spelled out to follow the user's naming rules, but the column labels the methods add to frames were kept exactly as the old code wrote them, because they are data rather than identifiers. Parameter renames shared by several modules:

| Old | New |
|---|---|
| `fastperiod`, `slowperiod`, `signalperiod` | `fast_period`, `slow_period`, `signal_period` |
| `ma_type`, `matype` | `moving_average_type` |
| `fast_ma_type`, `slow_ma_type`, `signal_ma_type` | `fast_moving_average_type`, `slow_moving_average_type`, `signal_moving_average_type` |
| `fastk_period`, `slowk_period`, `slowd_period`, `fastd_period` | `fast_k_period`, `slow_k_period`, `slow_d_period`, `fast_d_period` |
| `slowk_matype`, `slowd_matype`, `fastd_matype` | `slow_k_moving_average_type`, `slow_d_moving_average_type`, `fast_d_moving_average_type` |
| `nbdev` | `standard_deviations` |
| `column1`, `column2` | `first_column`, `second_column` |
| `talib as ta` | `talib` |

Each module's own note lists its method renames and anything odd carried over from the old code.
