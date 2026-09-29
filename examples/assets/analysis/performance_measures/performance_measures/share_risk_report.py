"""Print a one-page risk and return report for a share measured against the Nifty.

The program asks `performance_summary` for every measure of Infosys against the Nifty over one year, with a 6.5 percent risk-free rate, and prints the figures in three groups: return, risk and the comparison with the benchmark. It then prints the worst stretch of the year from `drawdowns`.

Typical usage example:

  .venv/bin/python examples/assets/analysis/performance_measures/performance_measures/share_risk_report.py
"""

import pandas as pd

from tradingmachine.assets import equities


class ShareRiskReport:
    """A risk and return report for one share against one benchmark.

    Attributes:
        share: The tradingmachine.assets.equities.Equity that is measured.
        benchmark: The tradingmachine.assets.equities.EquityIndex it is measured against.
        risk_free_rate: The float annual risk-free rate as a fraction.
        days: The int number of days the report covers.
    """

    def __init__(self):
        """Creates the report for Infosys against the Nifty over one year.

        Raises:
            Nothing.
        """
        self.share = equities.Equity(exchange="nse", symbol="INFY")
        self.benchmark = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        self.risk_free_rate = 0.065
        self.days = 365

    def print_group(
        self,
        title: str,
        summary: pd.Series,
        measures: list[str],
        percentages: list[str],
    ) -> None:
        """Prints one group of measures from the summary.

        Args:
            title: The str heading of the group.
            summary: The pandas.Series returned by `performance_summary`.
            measures: The list of str measure names to print, in order.
            percentages: The list of str measure names to print as percentages rather than as plain numbers.

        Returns:
            None.

        Raises:
            KeyError: A measure is not in the summary.
        """
        print(title)
        for measure in measures:
            value = summary[measure]
            label = measure.replace("_", " ")
            if value is None:
                print(f"  {label:<24}not available")
            elif measure in percentages:
                print(f"  {label:<24}{value:.2%}")
            else:
                print(f"  {label:<24}{value:.2f}")

    def print_worst_stretch(self) -> None:
        """Prints the peak before the worst drawdown of the period and the lowest point after it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        frame = self.share.drawdowns(days=self.days)
        if frame is None:
            return
        trough_position = frame["drawdown"].idxmin()
        trough = frame.loc[trough_position]
        before_trough = frame.loc[:trough_position]
        peak_position = before_trough["close"].idxmax()
        peak = frame.loc[peak_position]
        print("Worst stretch")
        print(f"  peak    {peak['datetime'].date()}  {peak['close']:.2f}")
        print(f"  trough  {trough['datetime'].date()}  {trough['close']:.2f}")
        print(f"  fall    {trough['drawdown']:.2%}")

    def run(self) -> None:
        """Calculates the summary and prints the report.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        summary = self.share.performance_summary(
            benchmark=self.benchmark,
            risk_free_rate=self.risk_free_rate,
            days=self.days,
        )
        if summary is None:
            print("UBI has too few Infosys candles for the report.")
            return
        percentages = [
            "cumulative_return",
            "annualised_return",
            "annualised_volatility",
            "maximum_drawdown",
            "value_at_risk",
            "expected_shortfall",
            "alpha",
            "tracking_error",
        ]
        print(f"INFY against the NIFTY over the last {self.days} days")
        self.print_group(
            "Return",
            summary,
            [
                "cumulative_return",
                "annualised_return",
                "sharpe_ratio",
                "sortino_ratio",
                "calmar_ratio",
            ],
            percentages,
        )
        self.print_group(
            "Risk",
            summary,
            [
                "annualised_volatility",
                "maximum_drawdown",
                "value_at_risk",
                "expected_shortfall",
            ],
            percentages,
        )
        self.print_group(
            "Against the benchmark",
            summary,
            [
                "benchmark_beta",
                "alpha",
                "tracking_error",
                "information_ratio",
                "up_capture_ratio",
                "down_capture_ratio",
            ],
            percentages,
        )
        self.print_worst_stretch()


if __name__ == "__main__":
    ShareRiskReport().run()
