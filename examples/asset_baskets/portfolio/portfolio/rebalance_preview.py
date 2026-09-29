"""Work out what it would take to move a portfolio to an index's weights, without trading.

The program describes a lopsided portfolio of three IT shares, builds an equally weighted index of four IT shares as the target, and prints the portfolio's current weights, the trades `rebalance_trades` works out for the portfolio's own value and for a larger sum of money, and the money each set of trades would move. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/asset_baskets/portfolio/portfolio/rebalance_preview.py
"""

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import index
from tradingmachine.asset_baskets import portfolio
from tradingmachine.assets import equities

HELD_QUANTITIES = {
    "INFY": 40,
    "TCS": 5,
    "WIPRO": 30,
}

TARGET_SYMBOLS = [
    "INFY",
    "TCS",
    "HCLTECH",
    "WIPRO",
]

LARGER_CAPITAL = 200000


class RebalancePreview:
    """A preview of the trades that would bring a portfolio to an index's weights.

    Attributes:
        held: The tradingmachine.asset_baskets.portfolio.Portfolio as it is held now.
        target: The tradingmachine.asset_baskets.index.Index whose weights are the goal.
    """

    def __init__(self):
        """Looks the shares up in UBI and builds the portfolio and the target.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
        """
        shares = {}
        for symbol in TARGET_SYMBOLS:
            shares[symbol] = equities.Equity(exchange="nse", symbol=symbol)
        held_members = []
        for symbol, quantity in HELD_QUANTITIES.items():
            held_members.append(
                basket_member.BasketMember(shares[symbol], quantity=quantity)
            )
        self.held = portfolio.Portfolio(name="IT shares held", members=held_members)
        target_members = []
        for symbol in TARGET_SYMBOLS:
            target_members.append(basket_member.BasketMember(shares[symbol]))
        self.target = index.Index(
            name="IT equal weight",
            members=target_members,
            weighting="equal",
        )

    def print_trades(self, heading: str, capital: float | None) -> None:
        """Prints the trades for one amount of capital and the money they move.

        Args:
            heading: The str heading to print first.
            capital: The float rupees to spread across the target, or None for the portfolio's value.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: An instrument has no last price.
        """
        trades = self.held.rebalance_trades(target=self.target, capital=capital)
        print(heading)
        print(
            trades[["label", "current_quantity", "target_quantity", "transaction_type"]]
        )
        turnover = (trades["trade_quantity"].abs() * trades["last_price"]).sum()
        print(f"Money moved: Rs {turnover:,.2f}")
        print()

    def run(self) -> None:
        """Prints the current weights and both previews.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: An instrument has no last price.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        print(f"Portfolio value: Rs {self.held.value:,.2f}")
        print(self.held.weights.round(3))
        print()
        self.print_trades("Trades at the portfolio's own value:", None)
        self.print_trades(f"Trades for Rs {LARGER_CAPITAL:,}:", LARGER_CAPITAL)


if __name__ == "__main__":
    RebalancePreview().run()
