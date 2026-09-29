"""Scan shares and NIFTY for closes outside their 20-day high and low channel.

The program reads three months of daily candles for each instrument through `maximum`, `minimum` and `minimum_maximum_index`, builds a channel from the highest high and lowest low of the 20 days before the latest session, and prints whether the latest close broke above it, broke below it or stayed inside, together with the dates on which the channel's high and low were made.

Typical usage example:

  .venv/bin/python examples/assets/analysis/math_operators/math_operators/channel_breakout_scan.py
"""

from tradingmachine.assets import equities


class ChannelBreakoutScan:
    """A scan for breakouts from a 20-day price channel.

    Attributes:
        instruments: A dict mapping a str label to the instrument that is scanned.
        window: The int number of candles in the channel.
        days: The int number of days of daily candles to read.
    """

    def __init__(self, window: int = 20, days: int = 90):
        """Creates the scan over the NIFTY 50 index and four shares.

        Args:
            window: The int number of candles in the channel.
            days: The int number of days of daily candles to read.

        Raises:
            Nothing.
        """
        self.instruments = {
            "NIFTY": equities.EquityIndex(exchange="nse", symbol="NIFTY"),
            "INFY": equities.Equity(exchange="nse", symbol="INFY"),
            "TCS": equities.Equity(exchange="nse", symbol="TCS"),
            "HDFCBANK": equities.Equity(exchange="nse", symbol="HDFCBANK"),
            "RELIANCE": equities.Equity(exchange="nse", symbol="RELIANCE"),
        }
        self.window = window
        self.days = days

    def classify(self, close: float, channel_high: float, channel_low: float) -> str:
        """Says where a close sits relative to the channel.

        Args:
            close: The float latest close.
            channel_high: The float highest high of the channel.
            channel_low: The float lowest low of the channel.

        Returns:
            The str `broke above`, `broke below` or `inside`.

        Raises:
            Nothing.
        """
        if close > channel_high:
            return "broke above"
        if close < channel_low:
            return "broke below"
        return "inside"

    def describe(self, label: str, instrument) -> str:
        """Scans one instrument.

        Args:
            label: The str name printed for the instrument.
            instrument: The tradingmachine.assets.instruments.Instrument that is scanned.

        Returns:
            A str line with the close, the channel, the verdict and the dates of the channel's extremes.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        high_frame = instrument.maximum(
            column="high",
            window=self.window,
            days=self.days,
        )
        if high_frame is None:
            return f"{label:<10} no candles"
        low_frame = instrument.minimum(
            column="low",
            window=self.window,
            days=self.days,
        )
        position_frame = instrument.minimum_maximum_index(
            column="close",
            window=self.window,
            days=self.days,
        )
        close = high_frame["close"].iloc[-1]
        channel_high = high_frame["max"].iloc[-2]
        channel_low = low_frame["min"].iloc[-2]
        verdict = self.classify(close, channel_high, channel_low)
        lowest_row = int(position_frame["minindex"].iloc[-1])
        highest_row = int(position_frame["maxindex"].iloc[-1])
        lowest_day = position_frame.loc[lowest_row, "datetime"].date()
        highest_day = position_frame.loc[highest_row, "datetime"].date()
        return (
            f"{label:<10} {close:>10.2f} {channel_low:>10.2f} "
            f"{channel_high:>10.2f}  {verdict:<12} "
            f"lowest close {lowest_day}, highest close {highest_day}"
        )

    def run(self) -> None:
        """Prints a header and one line per instrument.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print(f"{'Symbol':<10} {'Close':>10} {'Low':>10} {'High':>10}  Verdict")
        for label, instrument in self.instruments.items():
            print(self.describe(label, instrument))


if __name__ == "__main__":
    ChannelBreakoutScan().run()
