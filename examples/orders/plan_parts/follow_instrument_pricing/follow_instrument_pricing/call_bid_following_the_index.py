"""Build a bid for a Nifty call whose price follows the index rather than the option's own thin book.

The program finds the nearest weekly Nifty call closest to the index, and builds a plan order whose template is a limit buy of one lot at the call's last price, with an order that moves that price by half of every move in the index and keeps it within 20% of where it started. It prints the plan's synthetic object. The plan order is only built; nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/follow_instrument_pricing/follow_instrument_pricing/call_bid_following_the_index.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders import plan
from tradingmachine.orders.plan_parts import follow_instrument_pricing
from tradingmachine.orders.plan_parts import order_part


class CallBidFollowingTheIndex:
    """A bid for the at-the-money Nifty call that follows the index with a delta of one half.

    Attributes:
        index: The tradingmachine.assets.equities.EquityIndex for the Nifty 50 on the NSE.
        option: The tradingmachine.assets.equities.EquityIndexOption call nearest the index on the nearest expiry.
    """

    def __init__(self):
        """Looks up the index and the call nearest to it.

        Raises:
            ValueError: UBI has no last price for the index, or no call on its nearest expiry.
            tradingmachine.assets.exceptions.InstrumentError: The index or the option could not be found in UBI.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        index_price = self.index.last_price
        if index_price is None:
            raise ValueError(f"UBI has no last price for {self.index!r}")
        expiries = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        chain = equities.EquityIndexOption.chain(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiries[0],
        )
        calls = chain[chain["option_type"] == "CE"]
        nearest_strike = None
        nearest_distance = None
        for strike_price in calls["strike_price"]:
            distance = abs(strike_price - index_price)
            if nearest_distance is None or distance < nearest_distance:
                nearest_strike = strike_price
                nearest_distance = distance
        if nearest_strike is None:
            raise ValueError(f"UBI has no Nifty call expiring on {expiries[0]}")
        self.option = equities.EquityIndexOption(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiries[0],
            strike_price=nearest_strike,
            option_type="CE",
            underlying=self.index,
        )

    def run(self) -> None:
        """Prints the call, its price bounds and the plan's synthetic object.

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
                    instrument=self.index,
                    delta=0.5,
                    lowest=round(option_price * 0.8, 1),
                    highest=round(option_price * 1.2, 1),
                ),
            ),
        )
        print(f"Index at {self.index.last_price}")
        print(
            f"Call {self.option.strike_price} expiring {self.option.expiry_date}, last price {option_price}"
        )
        print(json.dumps(order.synthetic, indent=2))


if __name__ == "__main__":
    CallBidFollowingTheIndex().run()
