"""Follow a watchlist of bank shares and report what moved today.

The program builds a watchlist of five bank shares, adds a sixth, and prints the members ranked by today's move, the breadth of the list, the biggest gainer and loser, and the plain average move, since every member of a watchlist counts equally.

Typical usage example:

  .venv/bin/python examples/asset_baskets/watchlist/watchlist/bank_movers.py
"""

from tradingmachine.asset_baskets import watchlist
from tradingmachine.assets import equities

SYMBOLS = [
    "HDFCBANK",
    "ICICIBANK",
    "AXISBANK",
    "KOTAKBANK",
    "SBIN",
]

ADDED_SYMBOL = "INDUSINDBK"


class BankMovers:
    """A day's movers report on a watchlist of bank shares.

    Attributes:
        followed: The tradingmachine.asset_baskets.watchlist.Watchlist of bank shares.
    """

    def __init__(self):
        """Looks the shares up in UBI, builds the watchlist and adds one more share.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
        """
        banks = []
        for symbol in SYMBOLS:
            banks.append(equities.Equity(exchange="nse", symbol=symbol))
        self.followed = watchlist.Watchlist(name="banks", instruments=banks)
        self.followed.add(equities.Equity(exchange="nse", symbol=ADDED_SYMBOL))

    def run(self) -> None:
        """Prints the ranking, the breadth, the extremes and the average move.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        ranked = self.followed.rank_by("change_percent")
        print(ranked[["label", "last_price", "change_percent"]])
        breadth = self.followed.breadth
        print(
            f"Up {breadth['advancers']}, down {breadth['decliners']}, unchanged {breadth['unchanged']}"
        )
        gainer = self.followed.top_gainers(count=1)
        loser = self.followed.top_losers(count=1)
        if not gainer.empty and not loser.empty:
            print(f"Best {gainer.loc[0, 'label']}, worst {loser.loc[0, 'label']}")
        average = self.followed.day_change_percent
        if average is None:
            print("A member has no quote, so the average move is unknown.")
        else:
            print(f"Average move: {average:+.2f}%")


if __name__ == "__main__":
    BankMovers().run()
