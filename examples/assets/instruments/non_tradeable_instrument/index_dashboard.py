"""Print a dashboard of the main NSE indices.

The program builds each index as a NonTradeableInstrument, reads its level and its change on the day, and works out its return over the last month and the last year from UBI's daily candles.

Typical usage example:

  .venv/bin/python examples/assets/instruments/non_tradeable_instrument/index_dashboard.py
"""

from tradingmachine.assets import instruments


class IndexDashboard:
    """A dashboard of index levels and returns.

    Attributes:
        indices: A list of tradingmachine.assets.instruments.NonTradeableInstrument, one per index shown.
    """

    def __init__(self):
        """Looks each index up in UBI.

        Raises:
            tradingmachine.assets.exceptions.NonTradeableInstrumentError: A symbol names something that is not an index.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup.
        """
        symbols = [
            "NIFTY",
            "BANKNIFTY",
            "FINNIFTY",
            "MIDCPNIFTY",
        ]
        self.indices = []
        for symbol in symbols:
            index = instruments.NonTradeableInstrument(
                exchange="nse",
                segment="equity_indices",
                symbol=symbol,
            )
            self.indices.append(index)

    def return_over(
        self,
        index: instruments.NonTradeableInstrument,
        days: int,
    ) -> float | None:
        """Works out an index's return over a number of days from its daily closes.

        Args:
            index: The tradingmachine.assets.instruments.NonTradeableInstrument to measure.
            days: The int number of days to count back from today.

        Returns:
            The float return in per cent, or None when UBI has no candles for the range.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        candles = index.prices(interval="day", days=days)
        if candles is None:
            return None
        first_close = candles["close"].iloc[0]
        last_close = candles["close"].iloc[-1]
        return (last_close - first_close) / first_close * 100

    def format_percent(self, value: float | None) -> str:
        """Formats a percentage for the dashboard, or a dash when it is unknown.

        Args:
            value: The float percentage, or None.

        Returns:
            The str to print.

        Raises:
            Nothing.
        """
        if value is None:
            return "-"
        return f"{value:+.2f}%"

    def run(self) -> None:
        """Prints one line per index.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        print(f"{'Index':<12} {'Level':>10} {'Day':>9} {'Month':>9} {'Year':>9}")
        for index in self.indices:
            day = index.ohlc
            month_return = self.return_over(index, 30)
            year_return = self.return_over(index, 365)
            print(
                f"{index.symbol:<12} {day['last_price']:>10.2f} "
                f"{self.format_percent(day['change_percent']):>9} "
                f"{self.format_percent(month_return):>9} "
                f"{self.format_percent(year_return):>9}"
            )


if __name__ == "__main__":
    IndexDashboard().run()
