# assets/analysis/price_statistics.py

`PriceStatistics` holds the 39 summary statistics from the old `Instrument`, ported on 2026-09-14 with unchanged method names. Shared background is in `price_analysis.py.md`.

The methods form three families, each built on the one before:

```
prices()  ──►  price_high, price_low, price_mean ... price_histogram      (12)
          ──►  volumes()  ──►  volume_total, volume_high ... volume_histogram   (1 + 13)
          ──►  returns(column)  ──►  returns_high ... returns_summary       (1 + 12)
```

`volumes` and `returns` return a narrowed frame of `exchange`, `segment`, `datetime`, `interval` and the one value column. `returns` uses pandas' `pct_change`, so the first row is always empty.

The behaviour is carried over unchanged. `price_high` and `price_low` always read the `high` and `low` columns and take no `column` argument. The histogram methods draw with matplotlib through pandas and return the Axes, so they need a matplotlib backend; the live check used `Agg`.

The old docstring of `returns_quantile` described kurtosis; the new one describes the quantile it actually returns.
