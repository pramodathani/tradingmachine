"""Build a bid for a Nifty call priced at a chosen implied volatility off the index.

The program finds the nearest weekly Nifty call closest to the index and builds a plan order whose template is a limit buy of one lot at the call's last price, the most it will pay, with an order that UBI prices from the Black-76 model at 13% implied volatility, growing the index at 6.5% a year to expiry, and re-prices as the index moves. It prints the plan's synthetic object. The plan order is only built; nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/option_model_pricing/option_model_pricing/call_priced_at_an_implied_volatility.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders import plan
from tradingmachine.orders.plan_parts import option_model_pricing
from tradingmachine.orders.plan_parts import order_part


class CallAtAnImpliedVolatility:
    """A bid for the at-the-money Nifty call priced at 13% implied volatility.

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
        """Prints the call and the plan's synthetic object.

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
                pricing=option_model_pricing.OptionModelPricing(
                    instrument=self.index,
                    volatility=13.0,
                    interest_rate=6.5,
                ),
            ),
        )
        print(f"Index at {self.index.last_price}")
        print(
            f"Call {self.option.strike_price} expiring {self.option.expiry_date}, last price {option_price}"
        )
        print(json.dumps(order.synthetic, indent=2))


if __name__ == "__main__":
    CallAtAnImpliedVolatility().run()
