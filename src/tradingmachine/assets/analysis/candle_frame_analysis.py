"""Every analysis method, run over candles the caller already has.

`tradingmachine.assets.instruments.Instrument` inherits the analysis classes and fetches candles from UBI for each method call. `CandleFrameAnalysis` inherits the same classes but serves one DataFrame of candles given to it, so a program that has already read an instrument's candles, perhaps with extra history before the range it will show, can compute many indicators over them without asking UBI again.

Typical usage example:

  analysis = CandleFrameAnalysis(frame)
  rsi = analysis.relative_strength_index(window=14)["rsi_14"]
  macd = analysis.moving_average_convergence_divergence()
"""

import datetime

import pandas as pd

from tradingmachine.assets.analysis import candlestick_patterns
from tradingmachine.assets.analysis import cycle_indicators
from tradingmachine.assets.analysis import math_operators
from tradingmachine.assets.analysis import math_transforms
from tradingmachine.assets.analysis import momentum_indicators
from tradingmachine.assets.analysis import overlap_studies
from tradingmachine.assets.analysis import price_statistics
from tradingmachine.assets.analysis import price_transforms
from tradingmachine.assets.analysis import signals
from tradingmachine.assets.analysis import statistic_functions
from tradingmachine.assets.analysis import strategy_backtests
from tradingmachine.assets.analysis import volatility_indicators
from tradingmachine.assets.analysis import volume_indicators


class CandleFrameAnalysis(
    price_statistics.PriceStatistics,
    overlap_studies.OverlapStudies,
    momentum_indicators.MomentumIndicators,
    volume_indicators.VolumeIndicators,
    cycle_indicators.CycleIndicators,
    price_transforms.PriceTransforms,
    volatility_indicators.VolatilityIndicators,
    statistic_functions.StatisticFunctions,
    math_transforms.MathTransforms,
    math_operators.MathOperators,
    candlestick_patterns.CandlestickPatterns,
    signals.Signals,
    strategy_backtests.StrategyBacktests,
):
    """The analysis methods over one fixed DataFrame of candles.

    Each method works on its own copy of the candles, so the frame given is never changed and one method's added columns never appear in another's result. The range is fixed by the frame, so a method given from_date, to_date or days raises ValueError; interval and adjusted are ignored, because the frame already has them.
    """

    def __init__(self, frame: pd.DataFrame):
        """Initialises the analysis over a copy of the candles.

        Args:
            frame: A pandas.DataFrame of candles, oldest first, shaped like the frames `Instrument.prices` returns: at least the columns the methods to be called read, usually `open`, `high`, `low`, `close` and `volume` as float64, and `exchange`, `segment`, `interval` and `datetime` for the methods that label or line up candles by time, such as beta and the summaries.

        Raises:
            Nothing.
        """
        self._frame = frame.copy()

    def prices(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Returns a fresh copy of the candles given, for one analysis method to add its columns to.

        Args:
            interval: The str candle interval, which is ignored because the frame has one already.
            from_date: None, because the frame fixes the range.
            to_date: None, because the frame fixes the range.
            days: None, because the frame fixes the range.
            adjusted: A bool that is ignored because the frame has its price basis already.

        Returns:
            A pandas.DataFrame copy of the candles, or None when the frame has no rows.

        Raises:
            ValueError: from_date, to_date or days was given.
        """
        del interval, adjusted
        if from_date is not None or to_date is not None or days is not None:
            raise ValueError(
                "CandleFrameAnalysis serves one fixed frame of candles; from_date, to_date and days cannot be given"
            )
        if self._frame.empty:
            return None
        return self._frame.copy()
