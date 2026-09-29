"""List the days the Nifty's RSI left oversold or overbought ground in the last two years.

The program adds the 14-day relative strength index to two years of Nifty candles, adds constant columns for the levels 30 and 70, and uses `is_cross_over` to find the days the index rose out of oversold ground and `is_cross_under` to find the days it fell out of overbought ground.

Typical usage example:

  .venv/bin/python examples/assets/analysis/signals/signals/relative_strength_alerts.py
"""

import pandas as pd

from tradingmachine.assets import equities


class RelativeStrengthAlerts:
    """A list of the RSI threshold crossings of one index.

    Attributes:
        index: The tradingmachine.assets.equities.EquityIndex to read.
        oversold_level: The int RSI level below which the index counts as oversold.
        overbought_level: The int RSI level above which the index counts as overbought.
    """

    def __init__(self):
        """Creates the alerts over the Nifty with the usual levels of 30 and 70.

        Raises:
            Nothing.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        self.oversold_level = 30
        self.overbought_level = 70

    def print_events(self, label: str, events: pd.DataFrame) -> None:
        """Prints the date, close and RSI of each event.

        Args:
            label: The str description of the kind of event.
            events: The pandas.DataFrame of the marked rows.

        Returns:
            None.

        Raises:
            KeyError: events has no `datetime`, `close` or `rsi_14` column.
        """
        print(f"{label}: {len(events)}")
        for position in range(len(events)):
            row = events.iloc[position]
            event_date = row["datetime"].date()
            print(f"  {event_date}  close {row['close']:.2f}  RSI {row['rsi_14']:.1f}")

    def run(self) -> None:
        """Finds and prints both kinds of crossing.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        frame = self.index.relative_strength_index(window=14, days=730)
        if frame is None:
            print("UBI has no Nifty candles for the last two years.")
            return
        frame["oversold_level"] = self.oversold_level
        frame["overbought_level"] = self.overbought_level
        rises = self.index.is_cross_over(frame, "rsi_14", "oversold_level")
        falls = self.index.is_cross_under(frame, "rsi_14", "overbought_level")
        self.print_events(
            "Rose out of oversold ground",
            rises[rises["cross_over"]],
        )
        self.print_events(
            "Fell out of overbought ground",
            falls[falls["cross_under"]],
        )


if __name__ == "__main__":
    RelativeStrengthAlerts().run()
