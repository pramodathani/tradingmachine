"""Rank a watchlist by where each share trades within its day's range.

The program follows six large NSE shares, reads their day's prices in one request, works out where each last price sits between the day's low and high, and prints the list from the share nearest its low to the one nearest its high, with the list also ranked by last price for comparison.

Typical usage example:

  .venv/bin/python examples/asset_baskets/watchlist/watchlist/cheapest_by_range.py
"""

from tradingmachine.asset_baskets import watchlist
from tradingmachine.assets import equities

SYMBOLS = [
    "RELIANCE",
    "INFY",
    "HDFCBANK",
    "ITC",
    "LT",
    "BHARTIARTL",
]


class CheapestByRange:
    """A watchlist ranked by each share's position in its day's range.

    Attributes:
        followed: The tradingmachine.asset_baskets.watchlist.Watchlist being ranked.
    """

    def __init__(self):
        """Looks the shares up in UBI and builds the watchlist.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
        """
        shares = []
        for symbol in SYMBOLS:
            shares.append(equities.Equity(exchange="nse", symbol=symbol))
        self.followed = watchlist.Watchlist(name="large shares", instruments=shares)

    def run(self) -> None:
        """Prints the members ranked by their place in the day's range and by last price.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        frame = self.followed.ohlc
        day_range = frame["high"] - frame["low"]
        frame["place_in_range"] = (frame["last_price"] - frame["low"]) / day_range
        frame = frame.sort_values("place_in_range").reset_index(drop=True)
        print("Nearest the day's low first:")
        print(frame[["label", "low", "last_price", "high", "place_in_range"]].round(3))
        print()
        print("By last price, cheapest first:")
        print(
            self.followed.rank_by("last_price", ascending=True)[["label", "last_price"]]
        )


if __name__ == "__main__":
    CheapestByRange().run()
