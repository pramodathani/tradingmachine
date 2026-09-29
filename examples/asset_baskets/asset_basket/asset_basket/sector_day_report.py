"""Report how a weighted basket of IT shares is doing today.

The program builds a basket of five IT shares with their own weights, then prints its weights and concentration, the weighted move since yesterday's close, how many members are up and down, and the biggest gainer and loser, reading every member's prices from UBI in one request per table.

Typical usage example:

  .venv/bin/python examples/asset_baskets/asset_basket/asset_basket/sector_day_report.py
"""

from tradingmachine.asset_baskets import asset_basket
from tradingmachine.asset_baskets import basket_member
from tradingmachine.assets import equities

WEIGHTS = {
    "INFY": 30,
    "TCS": 30,
    "HCLTECH": 20,
    "WIPRO": 10,
    "TECHM": 10,
}


class SectorDayReport:
    """A day report on a weighted basket of IT shares.

    Attributes:
        basket: The tradingmachine.asset_baskets.asset_basket.AssetBasket being reported.
    """

    def __init__(self):
        """Looks every share up in UBI and builds the basket.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
        """
        members = []
        for symbol, weight in WEIGHTS.items():
            share = equities.Equity(exchange="nse", symbol=symbol)
            members.append(basket_member.BasketMember(share, weight=weight))
        self.basket = asset_basket.AssetBasket(name="IT shares", members=members)

    def print_weights(self) -> None:
        """Prints each member's weight and how concentrated the basket is.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(f"{self.basket.name}: {self.basket.size} members")
        for label, weight in self.basket.weights.items():
            print(f"  {label:<12} {weight:.0%}")
        effective = self.basket.effective_number_of_members
        print(f"Acts like {effective:.1f} equal members")

    def print_day(self) -> None:
        """Prints the basket's move, its breadth and its biggest movers.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        change = self.basket.day_change_percent
        if change is None:
            print("A member has no quote, so the day's move is unknown.")
        else:
            print(f"Weighted move today: {change:+.2f}%")
        breadth = self.basket.breadth
        print(f"Up {breadth['advancers']}, down {breadth['decliners']}")
        gainers = self.basket.top_gainers(count=1)
        losers = self.basket.top_losers(count=1)
        if not gainers.empty:
            print(
                f"Best:  {gainers.loc[0, 'label']} {gainers.loc[0, 'change_percent']:+.2f}%"
            )
        if not losers.empty:
            print(
                f"Worst: {losers.loc[0, 'label']} {losers.loc[0, 'change_percent']:+.2f}%"
            )

    def run(self) -> None:
        """Prints the whole report.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        self.print_weights()
        self.print_day()


if __name__ == "__main__":
    SectorDayReport().run()
