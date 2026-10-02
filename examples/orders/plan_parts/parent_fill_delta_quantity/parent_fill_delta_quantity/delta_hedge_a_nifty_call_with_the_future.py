"""Build a delta hedge: buy a Nifty call near the money and hedge each fill with the Nifty future, sized by the call's delta.

The program finds the soonest Nifty option expiry after today, the strike nearest the future's price, and the nearest Nifty future. The plan is meant to be placed on the call, because UBI works out the delta of the plan's own instrument: at each fill it takes the call's Black-76 delta at 13% volatility, with the future's last price as the forward, and sizes the hedge on the future to that delta times what filled, in whole lots. The hedge's side is `against_delta`, which sells the future against a bought call. It prints the call and the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/parent_fill_delta_quantity/parent_fill_delta_quantity/delta_hedge_a_nifty_call_with_the_future.py
"""

import datetime
import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import parent_fill_delta_quantity
from tradingmachine.orders.plan_parts import then_part


class DeltaHedgedCall:
    """A Nifty call bought and hedged with the Nifty future by its delta.

    Attributes:
        volatility_percent: The float volatility in percent the delta is worked out at.
    """

    def __init__(self):
        """Sets the volatility.

        Raises:
            Nothing.
        """
        self.volatility_percent = 13.0

    def soonest_after_today(self, expiries: list[datetime.date]) -> datetime.date:
        """Chooses the first expiry after today.

        Args:
            expiries: The list of datetime.date expiries, soonest first.

        Returns:
            The datetime.date of the chosen expiry.

        Raises:
            ValueError: No expiry is listed.
        """
        if not expiries:
            raise ValueError("No Nifty expiry is listed")
        today = datetime.date.today()
        for expiry in expiries:
            if expiry > today:
                return expiry
        return expiries[0]

    def run(self) -> None:
        """Finds the call and the future and prints the plan.

        Returns:
            None.

        Raises:
            ValueError: No expiry is listed, or UBI has no price for the future.
            tradingmachine.assets.exceptions.InstrumentError: UBI has no such contract.
        """
        future = equities.EquityIndexFutures(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=self.soonest_after_today(
                equities.EquityIndexFutures.expiries(
                    exchange="nse",
                    underlying_symbol="NIFTY",
                ),
            ),
        )
        forward = future.last_price
        if forward is None:
            raise ValueError(f"UBI has no last price for {future!r}")
        option_expiry = self.soonest_after_today(
            equities.EquityIndexOption.expiries(
                exchange="nse",
                underlying_symbol="NIFTY",
            ),
        )
        strikes = equities.EquityIndexOption.strikes(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=option_expiry,
        )
        nearest_strike = strikes[0]
        for strike in strikes:
            if abs(strike - forward) < abs(nearest_strike - forward):
                nearest_strike = strike
        call = equities.EquityIndexOption(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=option_expiry,
            strike_price=nearest_strike,
            option_type="CE",
            underlying=future,
        )
        plan = then_part.ThenPart(
            first=order_part.OrderPart(
                pricing=marketable_pricing.MarketablePricing(),
            ),
            each_fill=order_part.OrderPart(
                instrument=future,
                side="against_delta",
                product="nrml",
                pricing=marketable_pricing.MarketablePricing(),
                quantity=parent_fill_delta_quantity.ParentFillDeltaQuantity(
                    volatility=self.volatility_percent,
                    whole_lots=True,
                ),
            ),
        )
        print(
            f"Place the plan on the NIFTY {call.strike_price} {call.option_type} "
            f"expiring {call.expiry_date}, instrument {call.instrument_id}, "
            f"with the future at {forward}"
        )
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    DeltaHedgedCall().run()
