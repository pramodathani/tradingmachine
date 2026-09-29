"""Summarise a share's daily ranges, its open-to-close moves and the value it traded.

The program reads three months of Infosys daily candles through `subtract`, `divide`, `add` and `multiply`, and prints the average daily range in rupees and as a percentage, the number of days that closed above their open, the average midpoint, and the average and largest rupee value traded in a day.

Typical usage example:

  .venv/bin/python examples/assets/analysis/math_operators/math_operators/daily_range_statistics.py
"""

from tradingmachine.assets import equities


class DailyRangeStatistics:
    """A summary of how a share moves within each day.

    Attributes:
        share: The tradingmachine.assets.equities.Equity that is summarised.
        days: The int number of days of daily candles to read.
    """

    def __init__(self, days: int = 90):
        """Creates the summary over the Infosys share.

        Args:
            days: The int number of days of daily candles to read.

        Raises:
            Nothing.
        """
        self.share = equities.Equity(exchange="nse", symbol="INFY")
        self.days = days

    def run(self) -> None:
        """Reads the candles through the four operators and prints the summary.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        range_frame = self.share.subtract(days=self.days)
        if range_frame is None:
            print("UBI has no Infosys candles for the range.")
            return
        ratio_frame = self.share.divide(days=self.days)
        move_frame = self.share.divide(
            first_column="close",
            second_column="open",
            days=self.days,
        )
        midpoint_frame = self.share.add(days=self.days)
        value_frame = self.share.multiply(
            first_column="close",
            second_column="volume",
            days=self.days,
        )
        range_percent = (ratio_frame["quotient"] - 1) * 100
        up_days = (move_frame["quotient"] > 1).sum()
        midpoint = midpoint_frame["sum"] / 2
        crores = value_frame["product"] / 10000000
        print(f"Infosys over {len(range_frame)} sessions:")
        print(f"Average daily range: Rs {range_frame['difference'].mean():.2f}")
        print(f"Average daily range: {range_percent.mean():.2f}% of the low")
        print(f"Closed above the open on {up_days} days")
        print(f"Average midpoint of high and low: Rs {midpoint.mean():.2f}")
        print(f"Average value traded: Rs {crores.mean():.1f} crore")
        print(f"Largest value traded: Rs {crores.max():.1f} crore")


if __name__ == "__main__":
    DailyRangeStatistics().run()
