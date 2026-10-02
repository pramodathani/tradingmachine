"""Build a NIFTY calendar spread legged in, the far month sold for whatever the near month has bought.

The program finds the two nearest NIFTY futures contracts and builds a then join: a buy of two lots of the near month two ticks past the offer, followed under `each_fill` by a sell of the next month on the same terms. The second leg uses `TopUpExecution`, as UBI's `attached_hedge` and `legged_spread` presets do, so each fill of the first sends a new sell for what is missing rather than resizing one resting order. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/top_up_execution/top_up_execution/calendar_spread_legged_in.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part
from tradingmachine.orders.plan_parts import top_up_execution


class LeggedCalendarSpread:
    """A near-month NIFTY buy whose far-month sell is topped up with each fill.

    Attributes:
        near_month: The tradingmachine.assets.equities.EquityIndexFutures for the nearest NIFTY future.
        far_month: The tradingmachine.assets.equities.EquityIndexFutures for the next NIFTY future.
    """

    def __init__(self):
        """Finds the two nearest contracts.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: A contract could not be found in UBI.
        """
        expiries = equities.EquityIndexFutures.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        self.near_month = equities.EquityIndexFutures(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiries[0],
        )
        self.far_month = equities.EquityIndexFutures(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiries[1],
        )

    def run(self) -> None:
        """Prints the join's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        lot_size = int(self.near_month.lot_size)
        join = then_part.ThenPart(
            first=order_part.OrderPart(
                instrument=self.near_month,
                transaction_type="buy",
                quantity=2 * lot_size,
                product="nrml",
                pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
            ),
            each_fill=order_part.OrderPart(
                instrument=self.far_month,
                transaction_type="sell",
                product="nrml",
                pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
                execution=top_up_execution.TopUpExecution(),
            ),
        )
        print(
            f"Buying the {self.near_month.expiry_date} future, selling the {self.far_month.expiry_date} future"
        )
        print(json.dumps(join.document(), indent=2))


if __name__ == "__main__":
    LeggedCalendarSpread().run()
