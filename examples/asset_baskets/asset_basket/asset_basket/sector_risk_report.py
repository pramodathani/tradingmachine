"""Measure how the members of a basket of bank shares move together over a year.

The program builds an equally weighted basket of five bank shares and prints, over the last year of day candles, the correlation of their returns, each member's share of the basket's risk, the diversification ratio, what each member added to the basket's return, and the basket's own Sharpe ratio and maximum drawdown.

Typical usage example:

  .venv/bin/python examples/asset_baskets/asset_basket/asset_basket/sector_risk_report.py
"""

from tradingmachine.asset_baskets import asset_basket
from tradingmachine.asset_baskets import basket_member
from tradingmachine.assets import equities

SYMBOLS = [
    "HDFCBANK",
    "ICICIBANK",
    "AXISBANK",
    "KOTAKBANK",
    "SBIN",
]

DAYS = 365

RISK_FREE_RATE = 0.065


class SectorRiskReport:
    """A year's risk report on an equally weighted basket of bank shares.

    Attributes:
        basket: The tradingmachine.asset_baskets.asset_basket.AssetBasket being measured.
    """

    def __init__(self):
        """Looks every share up in UBI and builds the basket.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
        """
        members = []
        for symbol in SYMBOLS:
            share = equities.Equity(exchange="nse", symbol=symbol)
            members.append(basket_member.BasketMember(share))
        self.basket = asset_basket.AssetBasket(name="banks", members=members)

    def run(self) -> None:
        """Prints every measure over the last year.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: UBI answered an error for a member's candles.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        print("Correlation of daily returns:")
        print(self.basket.correlation_matrix(days=DAYS).round(2))
        print()
        print("Share of the basket's risk:")
        print(self.basket.risk_contributions(days=DAYS).round(3))
        print()
        ratio = self.basket.diversification_ratio(days=DAYS)
        print(f"Diversification ratio: {ratio:.2f}")
        print()
        print("What each member added to the return:")
        print(self.basket.return_contributions(days=DAYS).round(4))
        print()
        sharpe = self.basket.sharpe_ratio(risk_free_rate=RISK_FREE_RATE, days=DAYS)
        drawdown = self.basket.maximum_drawdown(days=DAYS)
        print(f"Sharpe ratio: {sharpe:.2f}")
        print(f"Maximum drawdown: {drawdown:.2%}")


if __name__ == "__main__":
    SectorRiskReport().run()
