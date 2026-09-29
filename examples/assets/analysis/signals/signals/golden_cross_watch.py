"""Report which shares on a watch list are in a golden-cross or a death-cross trend.

The program compares the 50-day and 200-day simple moving averages of each share over three years, finds the latest crossing in either direction with `is_cross_over` and `is_cross_under`, and prints the share's current trend with the date it began.

Typical usage example:

  .venv/bin/python examples/assets/analysis/signals/signals/golden_cross_watch.py
"""

import pandas as pd

from tradingmachine.assets import equities


class GoldenCrossWatch:
    """A trend report over a watch list of shares.

    Attributes:
        symbols: The list of str nse symbols to report on.
    """

    def __init__(self):
        """Creates the report over four large nse shares.

        Raises:
            Nothing.
        """
        self.symbols = [
            "INFY",
            "TCS",
            "RELIANCE",
            "HDFCBANK",
        ]

    def averages(self, share: equities.Equity) -> pd.DataFrame | None:
        """Builds one frame holding the 50-day and the 200-day averages of a share.

        Args:
            share: The tradingmachine.assets.equities.Equity to read.

        Returns:
            A pandas.DataFrame of three years of candles with `sma_50` and `sma_200` columns, or None when UBI has no candles.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        fast_frame = share.simple_moving_average(window=50, days=1095)
        slow_frame = share.simple_moving_average(window=200, days=1095)
        if fast_frame is None or slow_frame is None:
            return None
        fast_frame["sma_200"] = slow_frame["sma_200"]
        return fast_frame

    def latest_date(self, crossings: pd.DataFrame, column: str) -> pd.Timestamp | None:
        """Finds the date of the last marked row of a crossing frame.

        Args:
            crossings: The pandas.DataFrame returned by `is_cross_over` or `is_cross_under`.
            column: The str name of the bool column to read, `cross_over` or `cross_under`.

        Returns:
            The pandas.Timestamp of the last crossing, or None when there is none.

        Raises:
            KeyError: crossings has no column named column.
        """
        marked = crossings[crossings[column]]
        if marked.empty:
            return None
        return marked["datetime"].iloc[-1]

    def report(self, symbol: str) -> None:
        """Prints the current trend of one share.

        Args:
            symbol: The str nse symbol of the share.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        share = equities.Equity(exchange="nse", symbol=symbol)
        frame = self.averages(share)
        if frame is None:
            print(f"{symbol}: no candles")
            return
        golden = share.is_cross_over(frame, "sma_50", "sma_200")
        death = share.is_cross_under(frame, "sma_50", "sma_200")
        golden_date = self.latest_date(golden, "cross_over")
        death_date = self.latest_date(death, "cross_under")
        latest = frame.iloc[-1]
        if latest["sma_50"] > latest["sma_200"]:
            trend = "golden-cross trend"
            since = golden_date
        else:
            trend = "death-cross trend"
            since = death_date
        if since is None:
            print(f"{symbol}: {trend}, no crossing in three years")
        else:
            print(f"{symbol}: {trend} since {since.date()}")

    def run(self) -> None:
        """Prints the trend of every share on the watch list.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print("Trend by the 50-day and 200-day simple moving averages")
        for symbol in self.symbols:
            self.report(symbol)


if __name__ == "__main__":
    GoldenCrossWatch().run()
