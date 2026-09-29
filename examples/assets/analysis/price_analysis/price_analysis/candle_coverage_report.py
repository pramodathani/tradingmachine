"""Report how many daily candles a share, an index and a basket supply.

The program asks a share, the NIFTY 50 index and an equal-weighted watchlist of three IT shares for a year of daily candles through the `prices` method that `PriceAnalysis` declares, and prints how many candles each returned, the first and last dates, and the latest close.

Typical usage example:

  .venv/bin/python examples/assets/analysis/price_analysis/price_analysis/candle_coverage_report.py
"""

from tradingmachine.asset_baskets import watchlist
from tradingmachine.assets import equities


class CandleCoverageReport:
    """A report of the daily candles three different candle sources supply.

    Attributes:
        sources: A dict mapping a str label to the instrument or basket whose candles are read.
        days: The int number of days to count back from today.
    """

    def __init__(self, days: int = 365):
        """Creates the report over a share, an index and a watchlist.

        Args:
            days: The int number of days to count back from today.

        Raises:
            Nothing.
        """
        infosys = equities.Equity(exchange="nse", symbol="INFY")
        information_technology = watchlist.Watchlist(
            name="information technology",
            instruments=[
                infosys,
                equities.Equity(exchange="nse", symbol="TCS"),
                equities.Equity(exchange="nse", symbol="WIPRO"),
            ],
        )
        self.sources = {
            "Infosys share": infosys,
            "NIFTY 50 index": equities.EquityIndex(exchange="nse", symbol="NIFTY"),
            "IT watchlist": information_technology,
        }
        self.days = days

    def describe(self, label: str, candles) -> str:
        """Describes one source's candles in a single line.

        Args:
            label: The str name of the candle source.
            candles: The pandas.DataFrame of candles the source returned, or None when it had none.

        Returns:
            A str line naming the source, its candle count, its date range and its latest close.

        Raises:
            Nothing.
        """
        if candles is None:
            return f"{label}: no candles"
        first_date = candles["datetime"].iloc[0]
        last_date = candles["datetime"].iloc[-1]
        last_close = candles["close"].iloc[-1]
        return f"{label}: {len(candles)} candles from {first_date:%Y-%m-%d} to {last_date:%Y-%m-%d}, last close {last_close:.2f}"

    def run(self) -> None:
        """Reads each source's candles and prints one line for each.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        for label, source in self.sources.items():
            candles = source.prices(days=self.days)
            print(self.describe(label, candles))


if __name__ == "__main__":
    CandleCoverageReport().run()
