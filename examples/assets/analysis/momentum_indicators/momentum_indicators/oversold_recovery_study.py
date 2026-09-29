"""Study what NIFTY did after its relative strength index recovered from oversold.

The program reads two years of NIFTY 50 daily candles with the 14-day relative strength index and the slow stochastic oscillator, finds each day on which the relative strength index climbed back above 30, and prints the slow stochastic reading that day and how far the index moved over the following ten trading days.

Typical usage example:

  .venv/bin/python examples/assets/analysis/momentum_indicators/momentum_indicators/oversold_recovery_study.py
"""

from tradingmachine.assets import equities


class OversoldRecoveryStudy:
    """A study of the index's moves after each recovery from an oversold reading.

    Attributes:
        index: The tradingmachine.assets.equities.EquityIndex that is studied.
        days: The int number of days of daily candles to study.
        horizon: The int number of trading days after a recovery over which the move is measured.
    """

    def __init__(self, days: int = 730, horizon: int = 10):
        """Creates the study over the NIFTY 50 index.

        Args:
            days: The int number of days of daily candles to study.
            horizon: The int number of trading days after a recovery over which the move is measured.

        Raises:
            Nothing.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        self.days = days
        self.horizon = horizon

    def recovery_rows(self, relative_strength) -> list[int]:
        """Finds the rows on which the relative strength index crossed back above 30.

        Args:
            relative_strength: The pandas.Series of relative strength index values, one per candle.

        Returns:
            A list of int row positions, one for each recovery.

        Raises:
            Nothing.
        """
        rows = []
        for position in range(1, len(relative_strength)):
            previous = relative_strength.iloc[position - 1]
            current = relative_strength.iloc[position]
            if previous < 30 and current >= 30:
                rows.append(position)
        return rows

    def run(self) -> None:
        """Prints one line for each recovery and the average move after it.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        relative_strength_frame = self.index.relative_strength_index(
            window=14,
            days=self.days,
        )
        if relative_strength_frame is None:
            print("UBI has no NIFTY candles for the range.")
            return
        stochastic_frame = self.index.stochastic_oscillator(
            fast_k_period=14,
            days=self.days,
        )
        closes = relative_strength_frame["close"]
        rows = self.recovery_rows(relative_strength_frame["rsi_14"])
        print(f"Recoveries above 30 in the last {self.days} days: {len(rows)}")
        moves = []
        for row in rows:
            day = relative_strength_frame["datetime"].iloc[row].date()
            slow_k = stochastic_frame["slowk_3"].iloc[row]
            later_row = row + self.horizon
            if later_row >= len(closes):
                print(f"{day}  slow %K {slow_k:5.1f}  too recent to measure")
                continue
            move = (closes.iloc[later_row] / closes.iloc[row] - 1) * 100
            moves.append(move)
            print(
                f"{day}  slow %K {slow_k:5.1f}  next {self.horizon} days {move:+.2f}%"
            )
        if moves:
            average = sum(moves) / len(moves)
            print(f"Average move over {self.horizon} days: {average:+.2f}%")


if __name__ == "__main__":
    OversoldRecoveryStudy().run()
