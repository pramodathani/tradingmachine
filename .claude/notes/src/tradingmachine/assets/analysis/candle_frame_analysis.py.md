# src/tradingmachine/assets/analysis/candle_frame_analysis.py

`CandleFrameAnalysis` was added on 2026-09-26 for instruments_explorer, whose charts and screener used to compute TA-Lib indicators with their own code and now use this library's analysis methods instead.

## Why it exists

Every analysis method calls `self.prices(...)` and adds its columns to what comes back. On an `Instrument` that is one request to UBI per method call, which the library chose deliberately (see `docs/architecture/design-choices.md`). A chart that shows twelve indicators, or a screener that computes eight figures for 750 stocks, would send twelve or 6,000 requests for the same candles. It would also lose the chart's warm-up: instruments_explorer reads extra history before the first candle it shows, so a 200-day average has values from the chart's left edge, and then trims the extra part away, which a method that fetches its own range cannot do.

`CandleFrameAnalysis` inherits the same thirteen analysis classes in the same order as `Instrument`, and its `prices` returns a copy of one frame given to it. Every method therefore runs unchanged on candles the caller already has.

## Decisions

- **A copy per call.** `prices` returns `self._frame.copy()`, and the constructor copies the frame it is given. Each method adds its columns to its own copy, so the caller's frame never changes and the columns of one call never appear in the next. A frame of a few thousand candles copies in microseconds.
- **The range cannot be changed.** A method given `from_date`, `to_date` or `days` raises `ValueError` rather than silently answering for the whole frame, which would look right and be wrong. `interval` and `adjusted` are ignored, because the frame already has them, and every method passes them through.
- **The frame should look like `Instrument.prices` output.** The indicator methods only read `open`, `high`, `low`, `close` and `volume`, but a few methods label or line up rows by `exchange`, `segment`, `interval` and `datetime` (the summaries, `beta`, `correlation_coefficient`). The test builds its frame with all of them.
- **Missing volume is the caller's business.** TA-Lib carries a NaN volume forward to every later value of OBV, AD, ADOSC and MFI. instruments_explorer fills missing volume with zero before building the frame, which is what its own code did; this class does not change the frame it is given.
- `StrategyBacktests` is inherited too, so importing this module imports `backtesting`, as importing `Instrument` already does.

## Verified on 2026-09-26

All 188 inherited methods that need no argument ran on RELIANCE's 743 real daily candles and on the test frame without error, and left the frame unchanged. The five that need an argument are `beta` and `correlation_coefficient` (a benchmark, which may be another `CandleFrameAnalysis`), `is_cross_over` and `is_cross_under` (a frame and two columns) and `run_backtest` (a `backtesting` strategy).
