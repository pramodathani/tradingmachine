"""Look for divergence between price and on balance volume in a few shares.

The program reads two months of daily candles for each share, compares the change in its close with the change in its on balance volume over the last twenty sessions, and says whether volume confirms the price move or diverges from it.

Typical usage example:

  .venv/bin/python examples/assets/analysis/volume_indicators/volume_indicators/on_balance_volume_divergence.py
"""

from tradingmachine.assets import equities


class OnBalanceVolumeDivergence:
    """A check of whether volume agrees with each share's recent price move.

    Attributes:
        shares: A list of tradingmachine.assets.equities.Equity objects to check.
        sessions: The int number of sessions the change is measured over.
    """

    def __init__(self, sessions: int = 20):
        """Creates the check over five NSE shares.

        Args:
            sessions: The int number of sessions the change is measured over.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the shares.
        """
        symbols = [
            "RELIANCE",
            "INFY",
            "HDFCBANK",
            "TCS",
            "IDEA",
        ]
        self.shares = []
        for symbol in symbols:
            self.shares.append(equities.Equity(exchange="nse", symbol=symbol))
        self.sessions = sessions

    def verdict(self, price_change: float, volume_change: float) -> str:
        """Names the relationship between the two changes.

        Args:
            price_change: The float change in the close.
            volume_change: The float change in the on balance volume.

        Returns:
            The str verdict, `confirms` when both moved the same way and `diverges` otherwise.

        Raises:
            Nothing.
        """
        if price_change > 0 and volume_change > 0:
            return "confirms"
        if price_change < 0 and volume_change < 0:
            return "confirms"
        return "diverges"

    def run(self) -> None:
        """Prints each share's price change, volume change and verdict.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        for share in self.shares:
            candles = share.on_balance_volume(days=60)
            if candles is None or len(candles) <= self.sessions:
                print(f"{share.symbol}: not enough candles")
                continue
            start = -1 - self.sessions
            price_change = candles["close"].iloc[-1] - candles["close"].iloc[start]
            volume_change = candles["obv"].iloc[-1] - candles["obv"].iloc[start]
            percent = price_change / candles["close"].iloc[start] * 100
            print(
                f"{share.symbol:<10} price {percent:+6.2f}%  on balance volume {volume_change:+,.0f}  volume {self.verdict(price_change, volume_change)} the move"
            )


if __name__ == "__main__":
    OnBalanceVolumeDivergence().run()
