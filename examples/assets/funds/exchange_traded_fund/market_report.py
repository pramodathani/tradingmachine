"""Print a short market report on the NIFTYBEES exchange traded fund.

The program reads the fund's live values, a year of daily candles and its fourteen-day relative strength index, and says whether this account holds any units. It places no order.

Typical usage example:

  .venv/bin/python examples/assets/funds/exchange_traded_fund/market_report.py
"""

from tradingmachine.assets import funds


class MarketReport:
    """A one-screen report on one exchange traded fund.

    Attributes:
        fund: The funds.ExchangeTradedFund the report describes.
    """

    def __init__(self):
        """Looks NIFTYBEES up in UBI.

        Raises:
            tradingmachine.assets.exceptions.ExchangeTradedFundError: UBI has no such fund.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        self.fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")

    def run(self) -> None:
        """Prints the fund's identity, live values, year range, momentum and holding.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print(repr(self.fund))
        print(f"Tick size {self.fund.tick_size}, lot size {self.fund.lot_size}")
        self._print_live_values()
        self._print_year_range()
        self._print_momentum()
        self._print_holding()

    def _print_live_values(self) -> None:
        """Prints the last price and the day's open, high and low.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        quote = self.fund.ohlc
        day = quote["ohlc"]
        print(f"Last price: {quote['last_price']}")
        print(f"Previous close: {quote['previous_close']}")
        print(f"Today: open {day['open']}, high {day['high']}, low {day['low']}")

    def _print_year_range(self) -> None:
        """Prints the highest and lowest close of the last year and the year's return.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        candles = self.fund.prices(days=365)
        if candles is None:
            print("UBI has no candles for the last year.")
            return
        first_close = candles["close"].iloc[0]
        last_close = candles["close"].iloc[-1]
        year_return = (last_close / first_close - 1) * 100
        print(f"Year's closes: {len(candles)}")
        print(
            f"Highest close {candles['close'].max()}, lowest {candles['close'].min()}"
        )
        print(f"Return over the period: {year_return:.2f} per cent")

    def _print_momentum(self) -> None:
        """Prints the latest fourteen-day relative strength index.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        frame = self.fund.relative_strength_index(window=14, days=90)
        if frame is None:
            print("UBI has no candles to work the index out from.")
            return
        print(f"Relative strength index: {frame['rsi_14'].iloc[-1]:.1f}")

    def _print_holding(self) -> None:
        """Prints the units of the fund this account holds, if any.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        row = self.fund.holdings
        if row is None:
            print("This account holds no NIFTYBEES units.")
            return
        print(f"Held: {row['quantity']} units worth {self.fund.holdings_value}")
        print(f"Profit or loss: {self.fund.holdings_pnl}")


if __name__ == "__main__":
    MarketReport().run()
