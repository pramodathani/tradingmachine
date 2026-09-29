"""Measure how the Nifty moved in the week after an engulfing or a harami pattern.

The program fetches five years of Nifty candles through two pattern methods, then for each pattern splits the matches into bullish and bearish ones and prints how many there were and the average return over the following five candles.

Typical usage example:

  .venv/bin/python examples/assets/analysis/candlestick_patterns/candlestick_patterns/pattern_follow_through.py
"""

import pandas as pd

from tradingmachine.assets import equities


class PatternFollowThrough:
    """A study of what the index did after bullish and bearish pattern signals.

    Attributes:
        index: The tradingmachine.assets.equities.EquityIndex whose candles are studied.
        holding_candles: The int number of candles after a signal over which the return is measured.
    """

    def __init__(self):
        """Creates the study over the Nifty index on the nse.

        Raises:
            Nothing.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        self.holding_candles = 5

    def forward_returns(self, frame: pd.DataFrame) -> pd.Series:
        """Calculates each candle's return over the following holding period.

        Args:
            frame: The pandas.DataFrame of candles with a `close` column.

        Returns:
            A pandas.Series of fractional returns, which is NaN for the last candles that have no full holding period after them.

        Raises:
            KeyError: frame has no `close` column.
        """
        closes = frame["close"]
        later_closes = closes.shift(-self.holding_candles)
        return later_closes / closes - 1

    def describe(self, name: str, frame: pd.DataFrame, column: str) -> None:
        """Prints the count and average forward return of the bullish and bearish matches of one pattern.

        Args:
            name: The str name of the pattern to print.
            frame: The pandas.DataFrame the pattern method returned.
            column: The str name of the pattern column in frame.

        Returns:
            None.

        Raises:
            KeyError: frame has no column named column or no `close` column.
        """
        returns = self.forward_returns(frame)
        bullish_returns = returns[frame[column] > 0].dropna()
        bearish_returns = returns[frame[column] < 0].dropna()
        print(name)
        self.print_group("  bullish", bullish_returns)
        self.print_group("  bearish", bearish_returns)

    def print_group(self, label: str, returns: pd.Series) -> None:
        """Prints the size and mean of one group of forward returns.

        Args:
            label: The str label printed before the figures.
            returns: The pandas.Series of forward returns in the group.

        Returns:
            None.

        Raises:
            Nothing.
        """
        if returns.empty:
            print(f"{label}: no signal")
            return
        average = returns.mean()
        print(f"{label}: {len(returns)} signals, {average:.2%} over the next week")

    def run(self) -> None:
        """Runs both patterns over five years of candles and prints the study.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        engulfing_frame = self.index.candle_engulfing(days=1825)
        harami_frame = self.index.candle_harami(days=1825)
        if engulfing_frame is None or harami_frame is None:
            print("UBI has no Nifty candles for the last five years.")
            return
        print(f"Nifty over {len(engulfing_frame)} daily candles")
        self.describe("Engulfing", engulfing_frame, "candle_engulfing")
        self.describe("Harami", harami_frame, "candle_harami")


if __name__ == "__main__":
    PatternFollowThrough().run()
