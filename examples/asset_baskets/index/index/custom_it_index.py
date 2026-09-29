"""Build an equal-weighted IT index, follow its level and compare it with NIFTY IT.

The program builds an index of five IT shares that starts at 1000 on the first trading day of 2026, linked to the NSE's NIFTY IT index, and prints its level today, its last few day candles, its return and its tracking error against NIFTY IT over the year so far, and the same members under a price weighting for comparison.

Typical usage example:

  .venv/bin/python examples/asset_baskets/index/index/custom_it_index.py
"""

import datetime

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import index
from tradingmachine.assets import equities

SYMBOLS = [
    "INFY",
    "TCS",
    "HCLTECH",
    "WIPRO",
    "TECHM",
]

BASE_DATE = "2026-01-01"


class CustomItIndex:
    """An equal-weighted IT index linked to NIFTY IT.

    Attributes:
        nifty_it: The tradingmachine.assets.equities.EquityIndex for NIFTY IT.
        members: The list of tradingmachine.asset_baskets.basket_member.BasketMember in the index.
        it_index: The tradingmachine.asset_baskets.index.Index built from the members.
    """

    def __init__(self):
        """Looks the shares and NIFTY IT up in UBI and builds the index.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the instruments.
        """
        self.nifty_it = equities.EquityIndex(exchange="nse", symbol="NIFTYIT")
        self.members = []
        for symbol in SYMBOLS:
            share = equities.Equity(exchange="nse", symbol=symbol)
            self.members.append(basket_member.BasketMember(share))
        self.it_index = index.Index(
            name="my IT index",
            members=self.members,
            weighting="equal",
            base_value=1000,
            base_date=BASE_DATE,
            linked_instrument=self.nifty_it,
        )

    def run(self) -> None:
        """Prints the level, the candles, the comparison and the price weighting.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: A member has no candle or no last price.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        today = datetime.date.today()
        print(f"{self.it_index.name} level today: {self.it_index.level:.2f}")
        frame = self.it_index.prices(from_date=BASE_DATE, to_date=today)
        print(frame[["datetime", "close"]].tail().round(2))
        own_return = self.it_index.cumulative_return(from_date=BASE_DATE, to_date=today)
        official_return = self.nifty_it.cumulative_return(
            from_date=BASE_DATE, to_date=today
        )
        tracking = self.it_index.tracking_error(
            benchmark=self.nifty_it, from_date=BASE_DATE, to_date=today
        )
        print(f"Return this year: {own_return:+.2%}, NIFTY IT {official_return:+.2%}")
        print(f"Tracking error against NIFTY IT: {tracking:.2%}")
        price_weighted = index.Index(
            name="my IT index, price weighted",
            members=self.members,
            weighting="price",
        )
        print("Price weights:")
        print(price_weighted.weights.round(3))


if __name__ == "__main__":
    CustomItIndex().run()
