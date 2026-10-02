"""Build an offer for a Nifty put priced at a chosen implied volatility, using the nearest Nifty future as the forward.

The program finds the nearest Nifty future and the put on the nearest weekly expiry closest to its price, and builds a plan order whose template is a limit sell of one lot at the put's last price, the least it will take, with an order that UBI prices at 15% implied volatility from the future, which needs no interest rate because a future is already the forward. The premium is kept between half and twice the last price and moved in steps of two ticks. It prints the plan's synthetic object. The plan order is only built; nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/option_model_pricing/option_model_pricing/put_offer_priced_off_the_future.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders import plan
from tradingmachine.orders.plan_parts import option_model_pricing
from tradingmachine.orders.plan_parts import order_part


class PutOfferOffTheFuture:
    """An offer for the at-the-money Nifty put priced at 15% implied volatility off the future.

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
            transaction_type="sell",
            product="nrml",
            order_type="limit",
            quantity=int(self.option.lot_size),
            price=option_price,
            plan=order_part.OrderPart(
                pricing=option_model_pricing.OptionModelPricing(
                    instrument=self.future,
                    volatility=15.0,
                    lowest=round(option_price * 0.5, 1),
                    highest=round(option_price * 2, 1),
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
    PutOfferOffTheFuture().run()
