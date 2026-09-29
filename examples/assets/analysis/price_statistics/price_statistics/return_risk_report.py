"""Compare the risk in the daily returns of a share, an index and a basket.

The program reads a year of daily returns for Infosys, the NIFTY 50 index and an equal-weighted watchlist of three IT shares, and prints for each the annualised return and volatility, the skewness and excess kurtosis, and the fifth percentile daily return as a simple historical value at risk.

Typical usage example:

  .venv/bin/python examples/assets/analysis/price_statistics/price_statistics/return_risk_report.py
"""

from tradingmachine.asset_baskets import watchlist
from tradingmachine.assets import equities


class ReturnRiskReport:
    """A table of return and risk measures for several candle sources.

    Attributes:
        sources: A dict mapping a str label to the instrument or basket whose returns are measured.
        days: The int number of days to count back from today.
    """

    TRADING_DAYS_IN_A_YEAR = 252

    def __init__(self, days: int = 365):
        """Creates the report over a share, an index and a watchlist.

        Args:
            days: The int number of days to count back from today.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the instruments.
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
            "Infosys": infosys,
            "NIFTY 50": equities.EquityIndex(exchange="nse", symbol="NIFTY"),
            "IT watchlist": information_technology,
        }
        self.days = days

    def measure(self, source) -> dict:
        """Measures one source's returns.

        Args:
            source: The instrument or basket whose returns are measured.

        Returns:
            A dict of float measures keyed by `annual_return`, `annual_volatility`, `skewness`, `kurtosis` and `value_at_risk`.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        daily_mean = source.returns_mean(days=self.days)
        daily_deviation = source.returns_standard_deviation(days=self.days)
        return {
            "annual_return": daily_mean * self.TRADING_DAYS_IN_A_YEAR,
            "annual_volatility": daily_deviation * self.TRADING_DAYS_IN_A_YEAR**0.5,
            "skewness": source.returns_skewness(days=self.days),
            "kurtosis": source.returns_kurtosis(days=self.days),
            "value_at_risk": source.returns_quantile(quantile=0.05, days=self.days),
        }

    def run(self) -> None:
        """Prints one line of measures for each source.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print(
            f"{'Source':<14}{'Return':>9}{'Volatility':>12}{'Skewness':>10}{'Kurtosis':>10}{'5% day':>9}"
        )
        for label, source in self.sources.items():
            measures = self.measure(source)
            print(
                f"{label:<14}{measures['annual_return'] * 100:>8.1f}%{measures['annual_volatility'] * 100:>11.1f}%{measures['skewness']:>10.2f}{measures['kurtosis']:>10.2f}{measures['value_at_risk'] * 100:>8.2f}%"
            )


if __name__ == "__main__":
    ReturnRiskReport().run()
