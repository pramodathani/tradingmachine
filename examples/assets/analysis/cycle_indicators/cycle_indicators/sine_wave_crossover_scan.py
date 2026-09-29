"""Scan a few shares and a basket for recent Hilbert sine wave crossovers.

The program reads a year of daily candles for each candle source, finds every session in the last month on which the lead sine crossed the sine, and prints the most recent crossing with its direction, together with the phase of the dominant cycle and the two phasor components today.

Typical usage example:

  .venv/bin/python examples/assets/analysis/cycle_indicators/cycle_indicators/sine_wave_crossover_scan.py
"""

from tradingmachine.asset_baskets import watchlist
from tradingmachine.assets import equities


class SineWaveCrossoverScan:
    """A scan for sine wave crossovers, the Hilbert transform's turning signals.

    Attributes:
        sources: A dict mapping a str label to the instrument or basket to scan.
        days: The int number of days of candles to read.
        recent_sessions: The int number of recent sessions searched for a crossing.
    """

    def __init__(self, days: int = 365, recent_sessions: int = 22):
        """Creates the scan over three IT shares and a watchlist of them.

        Args:
            days: The int number of days of candles to read.
            recent_sessions: The int number of recent sessions searched for a crossing.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the shares.
        """
        symbols = [
            "INFY",
            "TCS",
            "WIPRO",
        ]
        self.sources = {}
        shares = []
        for symbol in symbols:
            share = equities.Equity(exchange="nse", symbol=symbol)
            self.sources[symbol] = share
            shares.append(share)
        self.sources["IT watchlist"] = watchlist.Watchlist(
            name="information technology", instruments=shares
        )
        self.days = days
        self.recent_sessions = recent_sessions

    def last_crossing(self, candles) -> str:
        """Finds the most recent crossing of the lead sine over or under the sine.

        Args:
            candles: A pandas.DataFrame with `datetime`, `sine` and `lead_sine` columns.

        Returns:
            A str naming the date and direction of the last crossing, or saying there was none.

        Raises:
            Nothing.
        """
        crossing = "no crossing in the period"
        first_position = len(candles) - self.recent_sessions
        for position in range(first_position, len(candles)):
            before = (
                candles["lead_sine"].iloc[position - 1]
                > candles["sine"].iloc[position - 1]
            )
            after = candles["lead_sine"].iloc[position] > candles["sine"].iloc[position]
            if after and not before:
                crossing = f"turned up on {candles['datetime'].iloc[position]:%Y-%m-%d}"
            if before and not after:
                crossing = (
                    f"turned down on {candles['datetime'].iloc[position]:%Y-%m-%d}"
                )
        return crossing

    def run(self) -> None:
        """Prints each source's last crossing, cycle phase and phasor components.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        for label, source in self.sources.items():
            sine_wave = source.hilbert_transform_sine_wave(days=self.days)
            if sine_wave is None:
                print(f"{label}: no candles")
                continue
            phase = source.hilbert_transform_dominant_cycle_phase(days=self.days)
            phasor = source.hilbert_transform_phasor_components(days=self.days)
            print(
                f"{label:<13} {self.last_crossing(sine_wave):<26} phase {phase['ht_dcphase'].iloc[-1]:7.1f} degrees  in-phase {phasor['inphase'].iloc[-1]:+.3f}  quadrature {phasor['quadrature'].iloc[-1]:+.3f}"
            )


if __name__ == "__main__":
    SineWaveCrossoverScan().run()
