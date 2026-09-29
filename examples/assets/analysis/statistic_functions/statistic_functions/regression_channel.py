"""Describe NIFTY's trend with a regression channel two standard deviations wide.

The program reads half a year of NIFTY 50 daily candles, fits a 50-day rolling regression line through the close, and prints the line's latest value, slope, angle and intercept, a channel two standard deviations either side of the line, and where the latest close sits in that channel.

Typical usage example:

  .venv/bin/python examples/assets/analysis/statistic_functions/statistic_functions/regression_channel.py
"""

from tradingmachine.assets import equities


class RegressionChannel:
    """A regression channel drawn around an index's close.

    Attributes:
        index: The tradingmachine.assets.equities.EquityIndex whose trend is described.
        window: The int number of candles the regression line is fitted over.
        days: The int number of days of daily candles to read.
    """

    def __init__(self, window: int = 50, days: int = 180):
        """Creates the channel over the NIFTY 50 index.

        Args:
            window: The int number of candles the regression line is fitted over.
            days: The int number of days of daily candles to read.

        Raises:
            Nothing.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        self.window = window
        self.days = days

    def latest(self, frame, column: str) -> float:
        """Gives the last value of one column.

        Args:
            frame: The pandas.DataFrame of candles with the column added.
            column: The str name of the column.

        Returns:
            The float value in the column's last row.

        Raises:
            KeyError: The frame has no such column.
        """
        return float(frame[column].iloc[-1])

    def run(self) -> None:
        """Fits the line, draws the channel and prints the description.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        line_frame = self.index.linear_regression(window=self.window, days=self.days)
        if line_frame is None:
            print("UBI has no NIFTY candles for the range.")
            return
        suffix = str(self.window)
        line = self.latest(line_frame, "lin_regr_" + suffix)
        slope = self.latest(
            self.index.linear_regression_slope(window=self.window, days=self.days),
            "lin_regr_slope_" + suffix,
        )
        angle = self.latest(
            self.index.linear_regression_angle(window=self.window, days=self.days),
            "lin_regr_angle_" + suffix,
        )
        intercept = self.latest(
            self.index.linear_regression_intercept(
                window=self.window,
                days=self.days,
            ),
            "lin_regr_int_" + suffix,
        )
        width = self.latest(
            self.index.standard_deviation(
                window=self.window,
                standard_deviations=2,
                days=self.days,
            ),
            "std_dev_" + suffix,
        )
        close = self.latest(line_frame, "close")
        print(f"Regression line {line:.2f}, intercept {intercept:.2f}")
        print(f"Slope {slope:+.2f} points a day, angle {angle:+.2f} degrees")
        print(f"Channel from {line - width:.2f} to {line + width:.2f}")
        position = (close - (line - width)) / (2 * width)
        print(f"Close {close:.2f} sits {position:.0%} of the way up the channel")


if __name__ == "__main__":
    RegressionChannel().run()
