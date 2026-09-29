"""Summarise a year of daily candles for a few instruments.

The program fetches one year of adjusted daily candles for each instrument in one request apiece, and prints its first and last close, its highest high and lowest low, its return over the year and how far the last close sits below the year's high.

Typical usage example:

  .venv/bin/python examples/assets/instruments/instrument/yearly_candle_summary.py
"""

import pandas as pd

from tradingmachine.assets import instruments


class YearlyCandleSummary:
    """A one-year summary of daily candles for several instruments.

    Attributes:
        summarised_instruments: A list of tradingmachine.assets.instruments.Instrument to summarise.
        days: The int number of days of candles to read, counting back from today.
    """

    def __init__(self, days: int = 365):
        """Looks the instruments up in UBI.

        Args:
            days: The int number of days of candles to read.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI has no instrument for one of the symbols.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup.
        """
        self.days = days
        self.summarised_instruments = [
            instruments.Instrument(
                exchange="nse",
                segment="equity_indices",
                symbol="NIFTY",
            ),
            instruments.Instrument(
                exchange="nse",
                segment="equities",
                symbol="TCS",
            ),
            instruments.Instrument(
                exchange="nse",
                segment="equities",
                symbol="ITC",
            ),
        ]

    def summarise(self, candles: pd.DataFrame) -> dict:
        """Works out the figures of the summary from one instrument's candles.

        Args:
            candles: The pandas.DataFrame that Instrument.prices returned.

        Returns:
            A dict with `first_close`, `last_close`, `high`, `low`, `return_percent` and `below_high_percent`, each a float.

        Raises:
            Nothing.
        """
        first_close = float(candles["close"].iloc[0])
        last_close = float(candles["close"].iloc[-1])
        high = float(candles["high"].max())
        low = float(candles["low"].min())
        return {
            "first_close": first_close,
            "last_close": last_close,
            "high": high,
            "low": low,
            "return_percent": (last_close - first_close) / first_close * 100,
            "below_high_percent": (high - last_close) / high * 100,
        }

    def run(self) -> None:
        """Prints the summary of every instrument.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        for instrument in self.summarised_instruments:
            candles = instrument.prices(interval="day", days=self.days)
            if candles is None:
                print(f"{instrument.symbol}: UBI has no candles")
                continue
            summary = self.summarise(candles)
            print(f"{instrument.symbol} over {len(candles)} sessions:")
            print(
                f"  close {summary['first_close']:.2f} -> {summary['last_close']:.2f}"
            )
            print(f"  range {summary['low']:.2f} - {summary['high']:.2f}")
            print(f"  return {summary['return_percent']:+.2f}%")
            print(f"  {summary['below_high_percent']:.2f}% below the year's high")


if __name__ == "__main__":
    YearlyCandleSummary().run()
