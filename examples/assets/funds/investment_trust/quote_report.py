"""Print a short market report on the EMBASSY real estate investment trust.

The program reads the trust's live quote and day range, confirms that UBI stores no candles for a trust, and says whether this account holds any units. It places no order.

Typical usage example:

  .venv/bin/python examples/assets/funds/investment_trust/quote_report.py
"""

from tradingmachine.assets import funds


class QuoteReport:
    """A one-screen report on one listed investment trust.

    Attributes:
        trust: The funds.InvestmentTrust the report describes.
    """

    def __init__(self):
        """Looks EMBASSY up in UBI.

        Raises:
            tradingmachine.assets.exceptions.InvestmentTrustError: UBI has no such trust.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        self.trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")

    def run(self) -> None:
        """Prints the trust's identity, live values, candles and holding.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print(repr(self.trust))
        print(f"Tick size {self.trust.tick_size}, lot size {self.trust.lot_size}")
        quote = self.trust.ohlc
        day = quote["ohlc"]
        change = (quote["last_price"] / quote["previous_close"] - 1) * 100
        print(f"Last price {quote['last_price']}, {change:.2f} per cent today")
        print(f"Today: open {day['open']}, high {day['high']}, low {day['low']}")
        candles = self.trust.prices(days=30)
        if candles is None:
            print("UBI stores no candles for a trust, so prices returned None.")
        else:
            print(f"UBI returned {len(candles)} candles.")
        row = self.trust.holdings
        if row is None:
            print("This account holds no EMBASSY units.")
        else:
            print(f"Held: {row['quantity']} units worth {self.trust.holdings_value}")
            print(f"Profit or loss: {self.trust.holdings_pnl}")


if __name__ == "__main__":
    QuoteReport().run()
