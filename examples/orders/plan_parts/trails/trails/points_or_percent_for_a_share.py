"""Choose a pullback distance for a share in rupees or as a percentage, and see the two side by side.

The program reads Vodafone Idea's last price, builds a `trails` condition 2% behind it as a percentage, and another with the same distance written in rupees, and prints both. A percentage keeps its meaning as the price moves, while rupees are easier to reason about for one trade. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/trails/trails/points_or_percent_for_a_share.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import trails


class PullbackDistance:
    """The same pullback distance for Vodafone Idea, as a percentage and in rupees.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
        percent: The float pullback distance as a percentage of the price.
    """

    def __init__(self):
        """Looks up the share and sets the distance.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")
        self.percent = 2.0

    def run(self) -> None:
        """Prints the last price and both conditions' objects.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        points = round(last_price * self.percent / 100, 2)
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(f"{self.percent}% of it is {points} rupees.")
        print(json.dumps(trails.Trails(percent=self.percent).document(), indent=2))
        print(json.dumps(trails.Trails(points=points).document(), indent=2))


if __name__ == "__main__":
    PullbackDistance().run()
