"""Build a bid for a Nifty put whose price follows the nearest Nifty future, falling as the future rises.

The program finds the nearest Nifty future and the put on the nearest weekly expiry closest to the future's price, and builds a plan order whose template is a limit buy of one lot at the put's last price, with an order that moves that price by minus 0.45 times every move in the future, only in steps of two ticks. It prints the plan's synthetic object. The plan order is only built; nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/follow_instrument_pricing/follow_instrument_pricing/put_bid_following_the_future.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders import plan
from tradingmachine.orders.plan_parts import follow_instrument_pricing
from tradingmachine.orders.plan_parts import order_part


class PutBidFollowingTheFuture:
    """A bid for the at-the-money Nifty put that follows the nearest Nifty future.

    Attributes:
        future: The tradingmachine.assets.equities.EquityIndexFutures for the nearest Nifty future.
        option: The tradingmachine.assets.equities.EquityIndexOption put nearest the future's price on the nearest expiry.
    """

    def __init__(self):
        """Looks up the future and the put nearest to it.

        Raises:
            ValueError: UBI has no last price for the future, or no put on the nearest expiry.
            tradingmachine.assets.exceptions.InstrumentError: The future or the option could not be found in UBI.
        """
        future_expiries = equities.EquityIndexFutures.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        self.future = equities.EquityIndexFutures(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=future_expiries[0],
        )
        future_price = self.future.last_price
        if future_price is None:
            raise ValueError(f"UBI has no last price for {self.future!r}")
        option_expiries = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        chain = equities.EquityIndexOption.chain(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=option_expiries[0],
        )
        puts = chain[chain["option_type"] == "PE"]
        nearest_strike = None
        nearest_distance = None
        for strike_price in puts["strike_price"]:
            distance = abs(strike_price - future_price)
            if nearest_distance is None or distance < nearest_distance:
                nearest_strike = strike_price
                nearest_distance = distance
        if nearest_strike is None:
            raise ValueError(f"UBI has no Nifty put expiring on {option_expiries[0]}")
        self.option = equities.EquityIndexOption(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=option_expiries[0],
            strike_price=nearest_strike,
            option_type="PE",
        )

    def run(self) -> None:
        """Prints the future, the put and the plan's synthetic object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the option.
        """
        option_price = self.option.last_price
        if option_price is None:
            raise ValueError(f"UBI has no last price for {self.option!r}")
        order = plan.PlanOrder(
            self.option,
            transaction_type="buy",
            product="nrml",
            order_type="limit",
            quantity=int(self.option.lot_size),
            price=option_price,
            plan=order_part.OrderPart(
                pricing=follow_instrument_pricing.FollowInstrumentPricing(
                    instrument=self.future,
                    delta=-0.45,
                    step_ticks=2,
                ),
            ),
        )
        print(f"Future expiring {self.future.expiry_date} at {self.future.last_price}")
        print(
            f"Put {self.option.strike_price} expiring {self.option.expiry_date}, last price {option_price}"
        )
        print(json.dumps(order.synthetic, indent=2))


if __name__ == "__main__":
    PutBidFollowingTheFuture().run()
