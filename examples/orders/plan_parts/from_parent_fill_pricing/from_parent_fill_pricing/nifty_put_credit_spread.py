"""Build a Nifty put credit spread, selling first and buying the protection at whatever price keeps the credit.

The program finds the nearest weekly Nifty put closest to the index and the put about 200 points below it, and builds a Then join: a sale of one lot of the nearer put at its last price, and on each of its fills a buy of the further put priced so that the two legs bring in the difference between their last prices. The net price is negative because the spread is a credit. It prints the join's object as UBI would read it. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/from_parent_fill_pricing/from_parent_fill_pricing/nifty_put_credit_spread.py
"""

import datetime
import json

import pandas as pd

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import from_parent_fill_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import then_part


class PutCreditSpread:
    """A Nifty put spread, sold near the money and bought about 200 points lower.

    Attributes:
        sold_put: The tradingmachine.assets.equities.EquityIndexOption put nearest the index.
        bought_put: The tradingmachine.assets.equities.EquityIndexOption put nearest 200 points below the index.
    """

    def __init__(self):
        """Looks up the index and the two puts.

        Raises:
            ValueError: UBI has no last price for the index, or no put on its nearest expiry.
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
        puts = chain[chain["option_type"] == "PE"]
        self.sold_put = self._put_nearest(puts, index_price, expiries[0])
        self.bought_put = self._put_nearest(puts, index_price - 200, expiries[0])

    def _put_nearest(
        self,
        puts: pd.DataFrame,
        price: float,
        expiry_date: datetime.date,
    ) -> equities.EquityIndexOption:
        """Looks up the put whose strike is nearest a price.

        Args:
            puts: The pandas.DataFrame of puts from the option chain.
            price: The float price the strike should be nearest.
            expiry_date: The datetime.date the puts expire on.

        Returns:
            The tradingmachine.assets.equities.EquityIndexOption put nearest the price.

        Raises:
            ValueError: The chain holds no puts.
            tradingmachine.assets.exceptions.InstrumentError: The option could not be found in UBI.
        """
        nearest_strike = None
        nearest_distance = None
        for strike_price in puts["strike_price"]:
            distance = abs(strike_price - price)
            if nearest_distance is None or distance < nearest_distance:
                nearest_strike = strike_price
                nearest_distance = distance
        if nearest_strike is None:
            raise ValueError(f"UBI has no Nifty put expiring on {expiry_date}")
        return equities.EquityIndexOption(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiry_date,
            strike_price=nearest_strike,
            option_type="PE",
        )

    def run(self) -> None:
        """Prints the two puts, the net price and the join's object.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for one of the puts.
        """
        sold_price = self.sold_put.last_price
        bought_price = self.bought_put.last_price
        if sold_price is None or bought_price is None:
            raise ValueError("UBI has no last price for one of the puts")
        net_price = round(bought_price - sold_price, 2)
        lot_size = int(self.sold_put.lot_size)
        part = then_part.ThenPart(
            first=order_part.OrderPart(
                instrument=self.sold_put,
                transaction_type="sell",
                quantity=lot_size,
                pricing=fixed_pricing.FixedPricing(
                    price=sold_price,
                    order_type="LIMIT",
                ),
            ),
            each_fill=order_part.OrderPart(
                instrument=self.bought_put,
                transaction_type="buy",
                pricing=from_parent_fill_pricing.FromParentFillPricing(
                    net_price=net_price,
                ),
            ),
        )
        print(f"Sell the {self.sold_put.strike_price} put at {sold_price}")
        print(f"Buy the {self.bought_put.strike_price} put, last at {bought_price}")
        print(f"Net price aimed at, negative for a credit: {net_price}")
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    PutCreditSpread().run()
