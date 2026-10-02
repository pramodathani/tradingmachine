"""Build a Nifty call debit spread whose second leg is priced from what the first leg filled at.

The program finds the nearest weekly Nifty call closest to the index and the call about 200 points above it, and builds a Then join: a buy of one lot of the nearer call at its last price, and on each of its fills a sale of the further call priced so that the spread costs the difference between their last prices. UBI works the sale's price out from the buy's average fill. It prints the join's object as UBI would read it. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/from_parent_fill_pricing/from_parent_fill_pricing/nifty_call_debit_spread.py
"""

import datetime
import json

import pandas as pd

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import from_parent_fill_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part


class CallDebitSpread:
    """A Nifty call spread, bought near the money and sold about 200 points higher.

    Attributes:
        bought_call: The tradingmachine.assets.equities.EquityIndexOption call nearest the index.
        sold_call: The tradingmachine.assets.equities.EquityIndexOption call nearest 200 points above the index.
    """

    def __init__(self):
        """Looks up the index and the two calls.

        Raises:
            ValueError: UBI has no last price for the index, or no call on its nearest expiry.
            tradingmachine.assets.exceptions.InstrumentError: The index or an option could not be found in UBI.
        """
        index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        index_price = index.last_price
        if index_price is None:
            raise ValueError(f"UBI has no last price for {index!r}")
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
        self.bought_call = self._call_nearest(calls, index_price, expiries[0])
        self.sold_call = self._call_nearest(calls, index_price + 200, expiries[0])

    def _call_nearest(
        self,
        calls: pd.DataFrame,
        price: float,
        expiry_date: datetime.date,
    ) -> equities.EquityIndexOption:
        """Looks up the call whose strike is nearest a price.

        Args:
            calls: The pandas.DataFrame of calls from the option chain.
            price: The float price the strike should be nearest.
            expiry_date: The datetime.date the calls expire on.

        Returns:
            The tradingmachine.assets.equities.EquityIndexOption call nearest the price.

        Raises:
            ValueError: The chain holds no calls.
            tradingmachine.assets.exceptions.InstrumentError: The option could not be found in UBI.
        """
        nearest_strike = None
        nearest_distance = None
        for strike_price in calls["strike_price"]:
            distance = abs(strike_price - price)
            if nearest_distance is None or distance < nearest_distance:
                nearest_strike = strike_price
                nearest_distance = distance
        if nearest_strike is None:
            raise ValueError(f"UBI has no Nifty call expiring on {expiry_date}")
        return equities.EquityIndexOption(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiry_date,
            strike_price=nearest_strike,
            option_type="CE",
        )

    def run(self) -> None:
        """Prints the two calls, the net price and the join's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for one of the calls.
        """
        bought_price = self.bought_call.last_price
        sold_price = self.sold_call.last_price
        if bought_price is None or sold_price is None:
            raise ValueError("UBI has no last price for one of the calls")
        net_price = round(bought_price - sold_price, 2)
        lot_size = int(self.bought_call.lot_size)
        part = then_part.ThenPart(
            first=order_part.OrderPart(
                instrument=self.bought_call,
                transaction_type="buy",
                quantity=lot_size,
                pricing=fixed_pricing.FixedPricing(
                    price=bought_price,
                    order_type="LIMIT",
                ),
            ),
            each_fill=order_part.OrderPart(
                instrument=self.sold_call,
                transaction_type="sell",
                pricing=from_parent_fill_pricing.FromParentFillPricing(
                    net_price=net_price,
                ),
            ),
        )
        print(f"Buy the {self.bought_call.strike_price} call at {bought_price}")
        print(f"Sell the {self.sold_call.strike_price} call, last at {sold_price}")
        print(f"Net debit aimed at: {net_price}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    CallDebitSpread().run()
