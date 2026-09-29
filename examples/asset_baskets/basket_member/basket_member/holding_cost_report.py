"""Compare what each holding cost with what it is worth now.

The program describes three holdings as basket members, each with a quantity and the average price it was bought at, and prints for each one its label, its cost, its value at the last price and the profit, using nothing but the member and its instrument.

Typical usage example:

  .venv/bin/python examples/asset_baskets/basket_member/basket_member/holding_cost_report.py
"""

from tradingmachine.asset_baskets import basket_member
from tradingmachine.assets import equities

QUANTITIES = {
    "IDEA": 100,
    "INFY": 5,
    "TCS": 2,
}

AVERAGE_PRICES = {
    "IDEA": 12.5,
    "INFY": 1450.0,
    "TCS": 3100.0,
}


class HoldingCostReport:
    """A cost and value report on a few holdings described as basket members.

    Attributes:
        members: The list of tradingmachine.asset_baskets.basket_member.BasketMember reported on.
    """

    def __init__(self):
        """Looks every share up in UBI and describes each holding as a member.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
        """
        self.members = []
        for symbol, quantity in QUANTITIES.items():
            share = equities.Equity(exchange="nse", symbol=symbol)
            member = basket_member.BasketMember(
                share,
                quantity=quantity,
                average_price=AVERAGE_PRICES[symbol],
            )
            self.members.append(member)

    def run(self) -> None:
        """Prints one line per holding and a total.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not give a last price.
        """
        total_profit = 0.0
        for member in self.members:
            cost = member.quantity * member.average_price
            value = member.quantity * member.instrument.last_price
            profit = value - cost
            total_profit += profit
            print(
                f"{member.label:<10} cost {cost:>10,.2f}  value {value:>10,.2f}  profit {profit:>+10,.2f}"
            )
        print(f"Total profit: {total_profit:+,.2f}")


if __name__ == "__main__":
    HoldingCostReport().run()
