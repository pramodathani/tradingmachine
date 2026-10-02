"""Build an exit that fires on a pullback from the best price or on a hard floor, whichever is reached first.

A trailing stop alone gives a winning trade room, but a trade that never rises leaves it far from the entry. The program reads Vodafone Idea's last price and joins a 3% pullback with a hard floor 2% below the market in an `AnyCondition` group. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/any_condition/any_condition/trail_with_a_hard_floor.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import any_condition
from tradingmachine.orders.plan_parts import price_crosses
from tradingmachine.orders.plan_parts import trails


class TrailWithFloor:
    """A pullback condition with a hard floor beside it.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
    """

    def __init__(self):
        """Looks up the share.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def run(self) -> None:
        """Prints the floor and the group's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        floor = round(last_price * 0.98, 2)
        group = any_condition.AnyCondition(
            [
                trails.Trails(percent=3.0),
                price_crosses.PriceCrosses(level=floor, direction="at_or_below"),
            ]
        )
        print(f"Last price of {self.share.symbol}: {last_price}, floor: {floor}")
        print(json.dumps(group.document(), indent=2))


if __name__ == "__main__":
    TrailWithFloor().run()
