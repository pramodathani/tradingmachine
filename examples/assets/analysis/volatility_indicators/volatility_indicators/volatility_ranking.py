"""Rank NSE shares from the most to the least volatile.

The program reads three months of daily candles for each share through the three volatility indicators that `VolatilityIndicators` gives every instrument, and prints the shares ranked by their latest average true range as a percentage of the close, alongside the average true range in rupees and the latest day's true range.

Typical usage example:

  .venv/bin/python examples/assets/analysis/volatility_indicators/volatility_indicators/volatility_ranking.py
"""

from tradingmachine.assets import equities


class VolatilityRanking:
    """A ranking of shares by how widely their prices range each day.

    Attributes:
        symbols: A list of str NSE symbols of the shares that are ranked.
        window: The int number of candles in each average true range window.
        days: The int number of days of daily candles to read for each share.
    """

    def __init__(self, window: int = 14, days: int = 90):
        """Creates the ranking over six NSE shares.

        Args:
            window: The int number of candles in each average true range window.
            days: The int number of days of daily candles to read for each share.

        Raises:
            Nothing.
        """
        self.symbols = [
            "INFY",
            "TCS",
            "HDFCBANK",
            "RELIANCE",
            "ITC",
            "IDEA",
        ]
        self.window = window
        self.days = days

    def measure(self, symbol: str) -> dict | None:
        """Reads one share's volatility indicators and keeps their latest values.

        Args:
            symbol: The str NSE symbol of the share.

        Returns:
            A dict with the str keys `symbol`, `close`, `average_true_range`, `normalized` and `true_range`, or None when UBI has no candles for the share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        share = equities.Equity(exchange="nse", symbol=symbol)
        average_frame = share.average_true_range(window=self.window, days=self.days)
        if average_frame is None:
            return None
        normalized_frame = share.normalized_average_true_range(
            window=self.window,
            days=self.days,
        )
        range_frame = share.true_range(days=self.days)
        return {
            "symbol": symbol,
            "close": average_frame["close"].iloc[-1],
            "average_true_range": average_frame[f"atr_{self.window}"].iloc[-1],
            "normalized": normalized_frame[f"natr{self.window}"].iloc[-1],
            "true_range": range_frame["tr"].iloc[-1],
        }

    def normalized_value(self, measurement: dict) -> float:
        """Gives the value the ranking sorts on.

        Args:
            measurement: A dict returned by measure.

        Returns:
            The float average true range as a percentage of the close.

        Raises:
            Nothing.
        """
        return measurement["normalized"]

    def run(self) -> None:
        """Measures every share and prints them from the most to the least volatile.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        measurements = []
        for symbol in self.symbols:
            measurement = self.measure(symbol)
            if measurement is None:
                print(f"{symbol}: no candles")
                continue
            measurements.append(measurement)
        measurements.sort(key=self.normalized_value, reverse=True)
        print(f"{'Symbol':<10} {'Close':>10} {'ATR':>9} {'ATR %':>7} {'Last TR':>9}")
        for measurement in measurements:
            print(
                f"{measurement['symbol']:<10} {measurement['close']:>10.2f} "
                f"{measurement['average_true_range']:>9.2f} "
                f"{measurement['normalized']:>6.2f}% "
                f"{measurement['true_range']:>9.2f}"
            )


if __name__ == "__main__":
    VolatilityRanking().run()
