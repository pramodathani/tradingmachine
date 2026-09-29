"""Print a momentum dashboard for a list of NSE shares and the NIFTY 50 index.

The program reads half a year of daily candles for each instrument through five of the momentum indicators that `MomentumIndicators` gives every instrument, and prints one line per instrument with the latest relative strength index, MACD histogram, average directional movement index, Williams %R and rate of change, followed by a one-word reading of the relative strength index.

Typical usage example:

  .venv/bin/python examples/assets/analysis/momentum_indicators/momentum_indicators/momentum_dashboard.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import instruments


class MomentumDashboard:
    """A one-line-per-instrument summary of momentum readings.

    Attributes:
        instruments: A dict mapping a str label to the instrument whose momentum is read.
        days: The int number of days of daily candles to read for each instrument.
    """

    def __init__(self, days: int = 180):
        """Creates the dashboard over four shares and the NIFTY 50 index.

        Args:
            days: The int number of days of daily candles to read for each instrument.

        Raises:
            Nothing.
        """
        self.instruments = {
            "NIFTY": equities.EquityIndex(exchange="nse", symbol="NIFTY"),
            "INFY": equities.Equity(exchange="nse", symbol="INFY"),
            "TCS": equities.Equity(exchange="nse", symbol="TCS"),
            "HDFCBANK": equities.Equity(exchange="nse", symbol="HDFCBANK"),
            "RELIANCE": equities.Equity(exchange="nse", symbol="RELIANCE"),
        }
        self.days = days

    def reading(self, relative_strength: float) -> str:
        """Turns a relative strength index value into a one-word reading.

        Args:
            relative_strength: The float relative strength index, between 0 and 100.

        Returns:
            The str `overbought` above 70, `oversold` below 30, and `neutral` otherwise.

        Raises:
            Nothing.
        """
        if relative_strength > 70:
            return "overbought"
        if relative_strength < 30:
            return "oversold"
        return "neutral"

    def describe(self, label: str, instrument: instruments.Instrument) -> str:
        """Reads one instrument's indicators and describes their latest values.

        Args:
            label: The str name printed for the instrument.
            instrument: The instrument whose indicators are read, a share or an index.

        Returns:
            A str line of the latest indicator values, or a line saying there were no candles.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        relative_strength_frame = instrument.relative_strength_index(
            window=14,
            days=self.days,
        )
        if relative_strength_frame is None:
            return f"{label:<10} no candles"
        convergence_frame = instrument.moving_average_convergence_divergence(
            days=self.days,
        )
        directional_frame = instrument.average_directional_movement_index(
            window=14,
            days=self.days,
        )
        williams_frame = instrument.williams_percent_r(window=14, days=self.days)
        change_frame = instrument.rate_of_change(window=20, days=self.days)
        relative_strength = relative_strength_frame["rsi_14"].iloc[-1]
        histogram = convergence_frame["macd_12_26_9_hist"].iloc[-1]
        directional_index = directional_frame["adx_14"].iloc[-1]
        williams = williams_frame["willr_14"].iloc[-1]
        change = change_frame["roc_20"].iloc[-1]
        return (
            f"{label:<10} {relative_strength:>6.1f} {histogram:>10.2f} "
            f"{directional_index:>6.1f} {williams:>8.1f} {change:>8.2f}  "
            f"{self.reading(relative_strength)}"
        )

    def run(self) -> None:
        """Prints a header and one line per instrument.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print(
            f"{'Symbol':<10} {'RSI 14':>6} {'MACD hist':>10} {'ADX 14':>6} "
            f"{'%R 14':>8} {'ROC 20':>8}  Reading"
        )
        for label, instrument in self.instruments.items():
            print(self.describe(label, instrument))


if __name__ == "__main__":
    MomentumDashboard().run()
