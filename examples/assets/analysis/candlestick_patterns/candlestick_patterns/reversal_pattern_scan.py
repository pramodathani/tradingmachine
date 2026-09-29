"""Scan a share for the common reversal candlestick patterns of the last month.

The program runs six well-known reversal patterns over two months of Infosys candles and prints, for each pattern, the dates in the last thirty days on which it appeared and whether each match was bullish or bearish.

Typical usage example:

  .venv/bin/python examples/assets/analysis/candlestick_patterns/candlestick_patterns/reversal_pattern_scan.py
"""

import datetime

import pandas as pd

from tradingmachine.assets import equities


class ReversalPatternScan:
    """A scan of one share for recent reversal candlestick patterns.

    Attributes:
        share: The tradingmachine.assets.equities.Equity whose candles are scanned.
        lookback_days: The int number of recent days whose matches are printed.
    """

    def __init__(self):
        """Creates the scan over Infosys on the nse.

        Raises:
            Nothing.
        """
        self.share = equities.Equity(exchange="nse", symbol="INFY")
        self.lookback_days = 30

    def pattern_frames(self) -> dict[str, tuple[pd.DataFrame, str]]:
        """Runs each reversal pattern over two months of candles.

        Returns:
            A dict mapping the str name of each pattern to a tuple (frame, column), where frame is the pandas.DataFrame the pattern method returned and column is the str name of its pattern column.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        days = self.lookback_days * 2
        return {
            "hammer": (
                self.share.candle_hammer(days=days),
                "candle_hammer",
            ),
            "hanging man": (
                self.share.candle_hanging_man(days=days),
                "candle_hangingman",
            ),
            "engulfing": (
                self.share.candle_engulfing(days=days),
                "candle_engulfing",
            ),
            "harami": (
                self.share.candle_harami(days=days),
                "candle_harami",
            ),
            "morning star": (
                self.share.candle_morning_star(days=days),
                "candle_morning_star",
            ),
            "evening star": (
                self.share.candle_evening_star(days=days),
                "candle_evening_star",
            ),
        }

    def recent_matches(self, frame: pd.DataFrame, column: str) -> pd.DataFrame:
        """Keeps the rows of the lookback period on which a pattern matched.

        Args:
            frame: The pandas.DataFrame a pattern method returned.
            column: The str name of the pattern column in frame.

        Returns:
            A pandas.DataFrame of the matching rows, which may be empty.

        Raises:
            KeyError: frame has no column named column.
        """
        today = datetime.date.today()
        first_day = today - datetime.timedelta(days=self.lookback_days)
        dates = frame["datetime"].dt.date
        is_recent = dates >= first_day
        is_match = frame[column] != 0
        return frame[is_recent & is_match]

    def run(self) -> None:
        """Scans every pattern and prints its recent matches.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print(f"Reversal patterns on INFY in the last {self.lookback_days} days")
        frames = self.pattern_frames()
        for name, frame_and_column in frames.items():
            frame, column = frame_and_column
            if frame is None:
                print(f"{name}: UBI has no candles")
                continue
            matches = self.recent_matches(frame, column)
            if matches.empty:
                print(f"{name}: no match")
                continue
            for position in range(len(matches)):
                row = matches.iloc[position]
                if row[column] > 0:
                    direction = "bullish"
                else:
                    direction = "bearish"
                match_date = row["datetime"].date()
                print(f"{name}: {direction} on {match_date}, close {row['close']}")


if __name__ == "__main__":
    ReversalPatternScan().run()
