"""Report the moving average trend of the NIFTY 50 index and a few shares.

The program reads about a year and a half of daily candles for each instrument, works out its fifty-day and two-hundred-day simple moving averages and its twenty-day exponential moving average, and prints whether the fifty-day average is above the two-hundred-day one, the golden cross, and whether the close is above the short average.

Typical usage example:

  .venv/bin/python examples/assets/analysis/overlap_studies/overlap_studies/moving_average_trend_report.py
"""

from tradingmachine.assets import equities


class MovingAverageTrendReport:
    """A trend report built from three moving averages of each instrument.

    Attributes:
        instruments: A list of the tradingmachine.assets.equities instruments to report on.
        days: The int number of days of candles to read, enough for the two-hundred-day average.
    """

    def __init__(self, days: int = 450):
        """Creates the report over the NIFTY 50 index and three shares.

        Args:
            days: The int number of days of candles to read.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the instruments.
        """
        self.instruments = [
            equities.EquityIndex(exchange="nse", symbol="NIFTY"),
            equities.Equity(exchange="nse", symbol="RELIANCE"),
            equities.Equity(exchange="nse", symbol="INFY"),
            equities.Equity(exchange="nse", symbol="HDFCBANK"),
        ]
        self.days = days

    def describe(self, instrument) -> str:
        """Describes one instrument's trend.

        Args:
            instrument: The instrument whose moving averages are read.

        Returns:
            A str line with the close, the three averages and the verdicts.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        fifty_day = instrument.simple_moving_average(window=50, days=self.days)
        two_hundred_day = instrument.simple_moving_average(window=200, days=self.days)
        twenty_day = instrument.exponential_moving_average(window=20, days=self.days)
        if fifty_day is None:
            return f"{instrument.symbol}: no candles"
        close = fifty_day["close"].iloc[-1]
        fifty_day_average = fifty_day["sma_50"].iloc[-1]
        two_hundred_day_average = two_hundred_day["sma_200"].iloc[-1]
        twenty_day_average = twenty_day["ema_20"].iloc[-1]
        if fifty_day_average > two_hundred_day_average:
            long_verdict = "golden cross"
        else:
            long_verdict = "death cross"
        if close > twenty_day_average:
            short_verdict = "above its 20-day average"
        else:
            short_verdict = "below its 20-day average"
        return f"{instrument.symbol:<10} close {close:>9.2f}  sma50 {fifty_day_average:>9.2f}  sma200 {two_hundred_day_average:>9.2f}  ema20 {twenty_day_average:>9.2f}  {long_verdict}, {short_verdict}"

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
    MovingAverageTrendReport().run()
