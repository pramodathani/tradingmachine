"""Report whether the NIFTY 50 index and a few shares are trending or cycling.

The program reads a year of daily candles for each instrument and uses the Hilbert transform to print its dominant cycle length, whether it is in a trend or a cycle today, how many of the last sixty sessions were trending, and how far the close sits from the instantaneous trend line.

Typical usage example:

  .venv/bin/python examples/assets/analysis/cycle_indicators/cycle_indicators/trend_or_cycle_report.py
"""

from tradingmachine.assets import equities


class TrendOrCycleReport:
    """A Hilbert transform report of each instrument's market mode.

    Attributes:
        instruments: A list of the tradingmachine.assets.equities instruments to report on.
        days: The int number of days of candles to read, enough for the Hilbert transform to settle.
        recent_sessions: The int number of recent sessions whose trend mode is counted.
    """

    def __init__(self, days: int = 365, recent_sessions: int = 60):
        """Creates the report over the NIFTY 50 index and three shares.

        Args:
            days: The int number of days of candles to read.
            recent_sessions: The int number of recent sessions whose trend mode is counted.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the instruments.
        """
        self.instruments = [
            equities.EquityIndex(exchange="nse", symbol="NIFTY"),
            equities.Equity(exchange="nse", symbol="INFY"),
            equities.Equity(exchange="nse", symbol="RELIANCE"),
            equities.Equity(exchange="nse", symbol="SBIN"),
        ]
        self.days = days
        self.recent_sessions = recent_sessions

    def describe(self, instrument) -> str:
        """Describes one instrument's cycle and trend.

        Args:
            instrument: The instrument whose candles are analysed.

        Returns:
            A str line with the cycle length, today's mode, the trending count and the distance from the trend line.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        period = instrument.hilbert_transform_dominant_cycle_period(days=self.days)
        mode = instrument.hilbert_transform_trend_mode(days=self.days)
        trend_line = instrument.hilbert_transform_trend_line(days=self.days)
        if period is None:
            return f"{instrument.symbol}: no candles"
        recent_modes = mode["ht_trendmode"].iloc[-self.recent_sessions :]
        trending_sessions = 0
        for value in recent_modes:
            if value == 1:
                trending_sessions += 1
        if mode["ht_trendmode"].iloc[-1] == 1:
            today = "trending"
        else:
            today = "cycling"
        close = trend_line["close"].iloc[-1]
        distance = (close / trend_line["ht_trendline"].iloc[-1] - 1) * 100
        return f"{instrument.symbol:<10} cycle {period['ht_dcperiod'].iloc[-1]:5.1f} days  today {today:<8}  trending {trending_sessions}/{self.recent_sessions}  from trend line {distance:+.2f}%"

    def run(self) -> None:
        """Prints one line for each instrument.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        for instrument in self.instruments:
            print(self.describe(instrument))


if __name__ == "__main__":
    TrendOrCycleReport().run()
