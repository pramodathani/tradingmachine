"""Work out how many Nifty futures lots would hedge a share portfolio.

A portfolio of shares loses money when the market falls, and selling index futures of the same value offsets that. The program values a small hypothetical portfolio at live prices, builds the next month's Nifty future, and prints how many lots, rounded down, bring the hedge closest to the portfolio's value without going over, and what fraction is left unhedged. It places no orders.

Typical usage example:

  .venv/bin/python examples/assets/instruments/index_futures/portfolio_hedge_ratio.py
"""

from tradingmachine.assets import equities


class PortfolioHedgeRatio:
    """A hedge of a share portfolio with Nifty futures.

    Attributes:
        share_counts: A dict mapping each str share symbol to the int number of shares held.
    """

    def __init__(self):
        """Stores the hypothetical portfolio.

        Raises:
            Nothing.
        """
        self.share_counts = {
            "RELIANCE": 400,
            "INFY": 500,
            "HDFCBANK": 600,
            "TCS": 200,
        }

    def portfolio_value(self) -> float:
        """Values the portfolio at the shares' last prices.

        Returns:
            The float value in rupees.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        total = 0.0
        for symbol, share_count in self.share_counts.items():
            share = equities.Equity(exchange="nse", symbol=symbol)
            total = total + share_count * share.last_price
        return total

    def run(self) -> None:
        """Prints the portfolio's value and the hedge.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        value = self.portfolio_value()
        expiries = equities.EquityIndexFutures.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        future = equities.EquityIndexFutures(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiries[1],
        )
        lot_value = future.contract_value
        lots = int(value // lot_value)
        hedged = lots * lot_value
        print(f"Portfolio worth Rs {value:,.0f}")
        print(f"{future} one lot of {future.lot_size} worth Rs {lot_value:,.0f}")
        print(f"Sell {lots} lots to hedge Rs {hedged:,.0f}")
        print(f"Unhedged: {(value - hedged) / value * 100:.1f}% of the portfolio")


if __name__ == "__main__":
    PortfolioHedgeRatio().run()
