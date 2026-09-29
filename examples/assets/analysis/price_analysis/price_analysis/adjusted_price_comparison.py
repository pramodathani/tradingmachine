"""Compare a share's adjusted and unadjusted daily closes.

The program reads five years of Reliance Industries' daily candles twice, once adjusted for splits and bonuses and once as traded, and prints the first close of each series and the number of days on which the two differ, which shows whether a corporate action fell inside the range.

Typical usage example:

  .venv/bin/python examples/assets/analysis/price_analysis/price_analysis/adjusted_price_comparison.py
"""

from tradingmachine.assets import equities


class AdjustedPriceComparison:
    """A comparison of one share's adjusted and unadjusted closes.

    Attributes:
        share: The tradingmachine.assets.equities.Equity whose candles are compared.
        days: The int number of days to count back from today.
    """

    def __init__(self, symbol: str = "RELIANCE", days: int = 1825):
        """Creates the comparison for one NSE share.

        Args:
            symbol: The str NSE symbol of the share.
            days: The int number of days to count back from today.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know the share.
        """
        self.share = equities.Equity(exchange="nse", symbol=symbol)
        self.days = days

    def count_differences(self, adjusted_closes, traded_closes) -> int:
        """Counts the days on which the two closes differ by more than a paisa.

        Args:
            adjusted_closes: A pandas.Series of closes adjusted for corporate actions.
            traded_closes: A pandas.Series of closes as traded, the same length as adjusted_closes.

        Returns:
            The int number of days whose two closes differ.

        Raises:
            Nothing.
        """
        differences = 0
        for adjusted_close, traded_close in zip(adjusted_closes, traded_closes):
            if abs(adjusted_close - traded_close) > 0.01:
                differences += 1
        return differences

    def run(self) -> None:
        """Reads both series and prints how they compare.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        adjusted = self.share.prices(days=self.days, adjusted=True)
        traded = self.share.prices(days=self.days, adjusted=False)
        if adjusted is None or traded is None:
            print(f"UBI has no candles for {self.share.symbol}.")
            return
        print(
            f"{self.share.symbol}: {len(adjusted)} adjusted candles, {len(traded)} traded candles"
        )
        print(f"First adjusted close: {adjusted['close'].iloc[0]:.2f}")
        print(f"First traded close: {traded['close'].iloc[0]:.2f}")
        if len(adjusted) != len(traded):
            print(
                "The two series have different lengths, so they are not compared day by day."
            )
            return
        differences = self.count_differences(adjusted["close"], traded["close"])
        print(f"Days whose closes differ: {differences}")


if __name__ == "__main__":
    AdjustedPriceComparison().run()
