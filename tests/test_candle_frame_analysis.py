"""Tests for CandleFrameAnalysis and the Mulloy TEMA method."""

import inspect
import math
import warnings

import numpy as np
import pandas as pd
import pytest
import talib

from tradingmachine.assets.analysis import candle_frame_analysis


def build_frame(count: int) -> pd.DataFrame:
    """Builds candles whose close follows a slow wave with a gentle rise.

    Args:
        count: The int number of candles.

    Returns:
        A pandas.DataFrame shaped like the frames Instrument.prices returns: `exchange`, `segment`, `interval`, `datetime` in India time, and float64 `open`, `high`, `low`, `close`, `volume` and `oi` columns.

    Raises:
        Nothing.
    """
    closes = []
    for index in range(count):
        closes.append(1000 + 50 * math.sin(index / 7) + index * 0.5)
    close = np.array(closes, dtype=np.float64)
    return pd.DataFrame(
        {
            "exchange": "nse",
            "segment": "nse_equities",
            "interval": "day",
            "datetime": pd.date_range(
                "2025-01-01", periods=count, freq="D", tz="Asia/Kolkata"
            ),
            "open": close - 2,
            "high": close + 6,
            "low": close - 7,
            "close": close,
            "volume": np.arange(count, dtype=np.float64) * 10 + 1000,
            "oi": np.zeros(count, dtype=np.float64),
        }
    )


class TestCandleFrameAnalysis:
    """The analysis methods run over a given frame without changing it."""

    def test_every_method_without_required_arguments_runs(self) -> None:
        """Checks that each such method returns a frame, a series or a number from the given candles.

        Raises:
            AssertionError: A method failed or returned nothing.
        """
        frame = build_frame(300)
        analysis = candle_frame_analysis.CandleFrameAnalysis(frame)
        ran = 0
        for name, function in inspect.getmembers(
            candle_frame_analysis.CandleFrameAnalysis, inspect.isfunction
        ):
            if name.startswith("_") or name == "prices":
                continue
            required = []
            for parameter in inspect.signature(function).parameters.values():
                if parameter.name != "self" and parameter.default is parameter.empty:
                    required.append(parameter.name)
            if required:
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = getattr(analysis, name)()
            assert result is not None, name
            ran += 1
        assert ran >= 180
        pd.testing.assert_frame_equal(frame, build_frame(300))

    def test_methods_do_not_share_columns(self) -> None:
        """Checks that one method's added column does not appear in the next method's result.

        Raises:
            AssertionError: A column leaked between calls.
        """
        analysis = candle_frame_analysis.CandleFrameAnalysis(build_frame(60))
        with_sma = analysis.simple_moving_average(window=5)
        with_rsi = analysis.relative_strength_index(window=5)
        assert "sma_5" in with_sma.columns
        assert "sma_5" not in with_rsi.columns

    def test_range_arguments_are_refused(self) -> None:
        """Checks that from_date, to_date and days raise, because the frame fixes the range.

        Raises:
            AssertionError: No ValueError was raised.
        """
        analysis = candle_frame_analysis.CandleFrameAnalysis(build_frame(30))
        with pytest.raises(ValueError, match="fixed frame"):
            analysis.simple_moving_average(days=365)
        with pytest.raises(ValueError, match="fixed frame"):
            analysis.prices(from_date="2026-01-01")
        assert analysis.prices(interval="5minute", adjusted=False) is not None

    def test_empty_frame_gives_none(self) -> None:
        """Checks that an empty frame behaves like UBI having no candles.

        Raises:
            AssertionError: A result was returned.
        """
        analysis = candle_frame_analysis.CandleFrameAnalysis(build_frame(0))
        assert analysis.relative_strength_index() is None

    def test_benchmark_methods_accept_another_frame(self) -> None:
        """Checks beta against a second analysis object as the benchmark.

        Raises:
            AssertionError: Beta was not computed.
        """
        stock = candle_frame_analysis.CandleFrameAnalysis(build_frame(120))
        benchmark = candle_frame_analysis.CandleFrameAnalysis(build_frame(120))
        result = stock.beta(benchmark, window=10)
        assert result is not None
        assert len(result) == 120

    def test_results_equal_talib_on_the_same_candles(self) -> None:
        """Checks a few results against TA-Lib called directly, exactly.

        Raises:
            AssertionError: A value differed.
        """
        frame = build_frame(200)
        analysis = candle_frame_analysis.CandleFrameAnalysis(frame)
        close = frame["close"].to_numpy()
        np.testing.assert_array_equal(
            analysis.relative_strength_index(window=14)["rsi_14"].to_numpy(),
            talib.RSI(close, timeperiod=14),
        )
        macd = analysis.moving_average_convergence_divergence(5, 35, 5)
        expected_macd, expected_signal, expected_histogram = talib.MACD(close, 5, 35, 5)
        np.testing.assert_array_equal(macd["macd_5_35_5"].to_numpy(), expected_macd)
        np.testing.assert_array_equal(
            macd["macd_5_35_5_signal"].to_numpy(), expected_signal
        )
        np.testing.assert_array_equal(
            macd["macd_5_35_5_hist"].to_numpy(), expected_histogram
        )


class TestMulloyTripleExponentialMovingAverage:
    """The TEMA method gives Mulloy's TEMA, not Tillson's T3."""

    def test_equals_talib_tema(self) -> None:
        """Checks the new column against talib.TEMA and that it differs from T3.

        Raises:
            AssertionError: The values were wrong.
        """
        frame = build_frame(200)
        analysis = candle_frame_analysis.CandleFrameAnalysis(frame)
        tema = analysis.mulloy_triple_exponential_moving_average(window=30)["tema_30"]
        np.testing.assert_array_equal(
            tema.to_numpy(),
            talib.TEMA(frame["close"].to_numpy(), timeperiod=30),
        )
        t3 = analysis.triple_exponential_moving_average(window=30)["t3_30"]
        assert not np.allclose(tema.to_numpy()[-50:], t3.to_numpy()[-50:])
