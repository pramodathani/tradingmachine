"""Build a protected trade in Vodafone Idea followed, once it is over, by a second entry after two in the afternoon.

The first child of the sequence is a then join: a buy whose every fill is protected by a stop and a target that reduce each other. The second child, a buy at two in the afternoon, is only considered once the whole first trade is done, which shows that a sequence can hold joins as well as orders. It prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/sequence_part/sequence_part/protected_trade_then_afternoon_reentry.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import either_part
from tradingmachine.orders.plan_parts import fixed_pricing
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import native_stop_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import sequence_part
from tradingmachine.orders.plan_parts import then_part
from tradingmachine.orders.plan_parts import time_at


class TradeThenReentry:
    """A bracketed trade, and a second entry started only after it.

    Attributes:
        share: The tradingmachine.assets.equities.Equity for Vodafone Idea on the NSE.
    """

    def __init__(self):
        """Looks the share up.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The share could not be found in UBI.
        """
        self.share = equities.Equity(exchange="nse", symbol="IDEA")

    def protected_trade(self, last_price: float) -> then_part.ThenPart:
        """Builds the first trade, a buy protected by a stop 3% below and a target 3% above.

        Args:
            last_price: The float last price the levels are measured from.

        Returns:
            The then_part.ThenPart holding the entry and its two exits.

        Raises:
            Nothing.
        """
        stop_trigger = round(last_price * 0.97, 2)
        target_price = round(last_price * 1.03, 2)
        return then_part.ThenPart(
            first=order_part.OrderPart(
                pricing=marketable_pricing.MarketablePricing(),
            ),
            each_fill=either_part.EitherPart(
                children=[
                    order_part.OrderPart(
                        side="protect",
                        pricing=native_stop_pricing.NativeStopPricing(
                            trigger_price=stop_trigger,
                            limit_price=round(stop_trigger - 0.05, 2),
                        ),
                    ),
                    order_part.OrderPart(
                        side="protect",
                        pricing=fixed_pricing.FixedPricing(
                            price=target_price,
                            order_type="LIMIT",
                        ),
                    ),
                ],
                sibling_rule="reduce",
            ),
        )

    def run(self) -> None:
        """Prints the plan.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = self.share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {self.share!r}")
        plan = sequence_part.SequencePart(
            children=[
                self.protected_trade(last_price),
                order_part.OrderPart(
                    trigger=time_at.TimeAt("14:00"),
                    pricing=marketable_pricing.MarketablePricing(),
                ),
            ],
        )
        print(f"Last price of {self.share.symbol}: {last_price}")
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    TradeThenReentry().run()
