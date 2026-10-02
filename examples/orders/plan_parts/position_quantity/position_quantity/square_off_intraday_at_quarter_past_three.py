"""Build a square-off: at a quarter past three, close every intraday position in the account, and separately close only two named shares.

The first plan closes every instrument held under the `intraday` position product, which is what the `square_off` synthetic order does. The second closes only Vodafone Idea and Yes Bank, and keeps their resting orders alive by turning `cancel_resting_first` off. Both use the `close` side, which a position quantity requires, and neither takes a pricing or execution, because UBI prices each closing order two ticks past the touch. It prints both plans. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/position_quantity/position_quantity/square_off_intraday_at_quarter_past_three.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import position_quantity
from tradingmachine.orders.plan_parts import time_at


class IntradaySquareOff:
    """Two afternoon closes, one of the whole intraday book and one of two shares.

    Attributes:
        shares: The list of tradingmachine.assets.equities.Equity closed by the second plan.
        close_time: The str time of day both closes fire.
    """

    def __init__(self):
        """Looks the two shares up.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: A share could not be found in UBI.
        """
        self.shares = [
            equities.Equity(exchange="nse", symbol="IDEA"),
            equities.Equity(exchange="nse", symbol="YESBANK"),
        ]
        self.close_time = "15:15"

    def run(self) -> None:
        """Prints both plans.

        Returns:
            None.

        Raises:
            Nothing.
        """
        every_position = order_part.OrderPart(
            trigger=time_at.TimeAt(self.close_time),
            side="close",
            quantity=position_quantity.PositionQuantity(
                product="intraday",
                every_instrument=True,
            ),
        )
        two_shares = order_part.OrderPart(
            trigger=time_at.TimeAt(self.close_time),
            side="close",
            quantity=position_quantity.PositionQuantity(
                product="intraday",
                held_instruments=self.shares,
                cancel_resting_first=False,
            ),
        )
        print("Every intraday position:")
        print(json.dumps(every_position.document(), indent=2))
        print("Only the two shares, leaving their resting orders alone:")
        print(json.dumps(two_shares.document(), indent=2))


if __name__ == "__main__":
    IntradaySquareOff().run()
