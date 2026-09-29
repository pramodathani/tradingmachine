"""Turn a weighted index into whole shares for a sum of money and preview the orders.

The program builds an index of four bank shares with stated weights, turns it into a portfolio of whole shares for one lakh rupees at last prices, prints the quantities, what they cost and how much money is left over, and asks UBI to build the market orders as a dry run, so nothing is sent to a broker.

Typical usage example:

  .venv/bin/python examples/asset_baskets/index/index/index_to_portfolio_orders.py
"""

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import index
from tradingmachine.assets import equities

WEIGHTS = {
    "HDFCBANK": 40,
    "ICICIBANK": 30,
    "AXISBANK": 15,
    "SBIN": 15,
}

CAPITAL = 100000


class IndexToPortfolioOrders:
    """A weighted bank index bought, on paper, for a fixed sum.

    Attributes:
        bank_index: The tradingmachine.asset_baskets.index.Index of bank shares.
    """

    def __init__(self):
        """Looks the shares up in UBI and builds the index.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
        """
        members = []
        for symbol, weight in WEIGHTS.items():
            share = equities.Equity(exchange="nse", symbol=symbol)
            members.append(basket_member.BasketMember(share, weight=weight))
        self.bank_index = index.Index(name="banks", members=members)

    def run(self) -> None:
        """Prints the portfolio for the capital and UBI's dry-run orders for it.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: A member has no last price.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        holdings = self.bank_index.to_portfolio(capital=CAPITAL)
        print(holdings.quantities)
        spent = holdings.value
        print(
            f"Spent Rs {spent:,.2f} of Rs {CAPITAL:,}, Rs {CAPITAL - spent:,.2f} left"
        )
        orders = holdings.place_orders(product="cnc", dry_run=True)
        print(orders[["label", "transaction_type", "quantity", "status"]])


if __name__ == "__main__":
    IndexToPortfolioOrders().run()
