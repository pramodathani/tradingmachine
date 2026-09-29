"""Scan a few shares and a basket for a Bollinger Band squeeze.

The program works out each candle source's twenty-day Bollinger Bands over the last six months, measures the band width as a percentage of the middle band, and reports a squeeze when today's width is in the narrowest fifth of the period, which traders read as a quiet spell that often comes before a larger move.

Typical usage example:

  .venv/bin/python examples/assets/analysis/overlap_studies/overlap_studies/bollinger_squeeze_scan.py
"""

from tradingmachine.asset_baskets import watchlist
from tradingmachine.assets import equities


class BollingerSqueezeScan:
    """A scan of several candle sources for narrow Bollinger Bands.

    Attributes:
        sources: A dict mapping a str label to the instrument or basket to scan.
        window: The int number of candles in the bands' moving average.
        days: The int number of days of candles to read.
    """

    def __init__(self, window: int = 20, days: int = 182):
        """Creates the scan over four banks and a watchlist of them.

        Args:
            window: The int number of candles in the bands' moving average.
            days: The int number of days of candles to read.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the shares.
        """
        symbols = [
            "HDFCBANK",
            "ICICIBANK",
            "SBIN",
            "AXISBANK",
        ]
        self.sources = {}
        banks = []
        for symbol in symbols:
            share = equities.Equity(exchange="nse", symbol=symbol)
            self.sources[symbol] = share
            banks.append(share)
        self.sources["bank watchlist"] = watchlist.Watchlist(
            name="banks", instruments=banks
        )
        self.window = window
        self.days = days

    def band_widths(self, source):
        """Works out the band width of every candle as a percentage of the middle band.

        Args:
            source: The instrument or basket whose bands are read.

        Returns:
            A pandas.Series of float widths without the warm-up candles, or None when there are no candles.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        candles = source.bollinger_bands(window=self.window, days=self.days)
        if candles is None:
            return None
        upper = candles[f"bb_upper_{self.window}"]
        lower = candles[f"bb_lower_{self.window}"]
        middle = candles[f"bb_middle_{self.window}"]
        widths = (upper - lower) / middle * 100
        return widths.dropna()

    def run(self) -> None:
        """Prints each source's width today, its narrowest-fifth threshold and the verdict.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        for label, source in self.sources.items():
            widths = self.band_widths(source)
            if widths is None or widths.empty:
                print(f"{label}: no candles")
                continue
            today = widths.iloc[-1]
            threshold = widths.quantile(0.2)
            if today <= threshold:
                verdict = "squeeze"
            else:
                verdict = "no squeeze"
            print(
                f"{label:<15} width {today:5.2f}%  narrowest fifth below {threshold:5.2f}%  {verdict}"
            )


if __name__ == "__main__":
    BollingerSqueezeScan().run()
