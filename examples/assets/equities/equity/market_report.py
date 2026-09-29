"""Print a short market report on one listed share.

The program looks Vodafone Idea up on the nse, reads its live quote and order book, works out a few measures from a year of daily candles, and says whether the account holds any of it.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity/market_report.py
"""

from tradingmachine.assets import equities


class ShareMarketReport:
    """A market report on one share listed on the nse.

    Attributes:
        share: The tradingmachine.assets.equities.Equity the report describes.
    """

    def __init__(self, symbol: str = "IDEA"):
        """Looks the share up in UBI.

        Args:
            symbol: The str nse symbol of the share, such as `IDEA`.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI has no nse share with that symbol.
        """
        self.share = equities.Equity(exchange="nse", symbol=symbol)

    def run(self) -> None:
        """Prints the live prices, the yearly measures and the holding.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        print(f"{self.share.symbol} on the {self.share.exchange}")
        print(f"Tick size: {self.share.tick_size}")
        print(f"Last price: {self.share.last_price}")
        print(f"Best bid: {self.share.best_bid}")
        print(f"Best offer: {self.share.best_offer}")
        print(f"Spread: {self.share.bid_offer_spread}")
        print(f"Volume today: {self.share.total_traded_volume}")
        self._print_yearly_measures()
        self._print_holding()

    def _print_yearly_measures(self) -> None:
        """Prints the latest relative strength index and the year's volatility and drawdown.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        strength_frame = self.share.relative_strength_index(window=14, days=365)
        if strength_frame is None:
            print("UBI has no candles for the last year.")
            return
        latest_strength = strength_frame["rsi_14"].iloc[-1]
        print(f"Relative strength index (14 days): {latest_strength:.1f}")
        volatility = self.share.annualised_volatility(days=365)
        print(f"Annualised volatility: {volatility:.1%}")
        drawdown = self.share.maximum_drawdown(days=365)
        print(f"Maximum drawdown over the year: {drawdown:.1%}")

    def _print_holding(self) -> None:
        """Prints the holding of the share, or says that none is held.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        holding = self.share.holdings
        if holding is None:
            print("The account holds none of this share.")
            return
        print(f"Held: {holding['quantity']} at {holding['average_price']}")
        print(f"Holding value: {self.share.holdings_value}")


if __name__ == "__main__":
    ShareMarketReport().run()
