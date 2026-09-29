"""Report where a few shares trade within their fifty-two-week range.

The program reads a year of daily candles for each share in a list and prints its fifty-two-week high and low, its average close, and where its latest close sits in that range, from 0 at the low to 100 at the high.

Typical usage example:

  .venv/bin/python examples/assets/analysis/price_statistics/price_statistics/fifty_two_week_range_report.py
"""

from tradingmachine.assets import equities


class FiftyTwoWeekRangeReport:
    """A report of several NSE shares' positions within their yearly range.

    Attributes:
        shares: A list of tradingmachine.assets.equities.Equity objects to report on.
    """

    def __init__(self):
        """Creates the report over four large NSE shares.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the shares.
        """
        symbols = [
            "RELIANCE",
            "INFY",
            "HDFCBANK",
            "TCS",
        ]
        self.shares = []
        for symbol in symbols:
            self.shares.append(equities.Equity(exchange="nse", symbol=symbol))

    def report_share(self, share: equities.Equity) -> str:
        """Works out one share's position in its range.

        Args:
            share: The tradingmachine.assets.equities.Equity to report on.

        Returns:
            A str line with the share's low, high, average close and position in the range.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        year_high = share.price_high(days=365)
        year_low = share.price_low(days=365)
        average_close = share.price_mean(days=365)
        if year_high is None or year_low is None:
            return f"{share.symbol}: no candles"
        last_close = share.prices(days=10)["close"].iloc[-1]
        position = (last_close - year_low) / (year_high - year_low) * 100
        return f"{share.symbol:<10} low {year_low:>9.2f}  high {year_high:>9.2f}  average {average_close:>9.2f}  last {last_close:>9.2f}  position {position:5.1f}"

    def run(self) -> None:
        """Prints one line for each share.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print("Fifty-two-week range, where position 0 is the low and 100 is the high")
        for share in self.shares:
            print(self.report_share(share))


if __name__ == "__main__":
    FiftyTwoWeekRangeReport().run()
