"""Print a trend and risk report on an equity index.

The program reads the Nifty 50's level and today's range, then works out its momentum, return, volatility and worst fall over the last year from daily candles.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity_index/index_trend_report.py
"""

from tradingmachine.assets import equities


class IndexTrendReport:
    """A trend and risk report on one equity index.

    Attributes:
        index: The tradingmachine.assets.equities.EquityIndex the report describes.
    """

    def __init__(self, symbol: str = "NIFTY"):
        """Looks the index up in UBI.

        Args:
            symbol: The str nse symbol of the index, such as `NIFTY`.

        Raises:
            tradingmachine.assets.exceptions.EquityIndexError: UBI has no nse index with that symbol.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol=symbol)

    def run(self) -> None:
        """Prints the level, the day's range and the yearly measures.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        print(f"{self.index.symbol}: {self.index.last_price}")
        day = self.index.ohlc
        day_range = day["ohlc"]
        print(f"Open {day_range['open']}, high {day_range['high']}")
        print(f"Low {day_range['low']}, previous close {day['previous_close']}")
        print(f"Change today: {day['change_percent']}%")
        strength_frame = self.index.relative_strength_index(window=14, days=365)
        if strength_frame is None:
            print("UBI has no candles for the last year.")
            return
        latest_strength = strength_frame["rsi_14"].iloc[-1]
        print(f"Relative strength index (14 days): {latest_strength:.1f}")
        print(f"Return over the year: {self.index.cumulative_return(days=365):.1%}")
        print(f"Volatility: {self.index.annualised_volatility(days=365):.1%}")
        print(f"Worst fall: {self.index.maximum_drawdown(days=365):.1%}")


if __name__ == "__main__":
    IndexTrendReport().run()
