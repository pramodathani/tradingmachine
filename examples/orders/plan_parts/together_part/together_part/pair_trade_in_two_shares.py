"""Build a pair trade: buy Vodafone Idea and sell Yes Bank at the same moment, each leg trading its own quantity.

The program looks both shares up, sizes each leg to about 20,000 rupees from its last price, and joins a buy of one and a sell of the other in a together join. The join keeps UBI's default `group_margin`, so the broker selector chooses one broker that can afford both legs. It prints the plan. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/together_part/together_part/pair_trade_in_two_shares.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import together_part


class PairTrade:
    """A long leg in Vodafone Idea and a short leg in Yes Bank, started together.

    Attributes:
        long_share: The tradingmachine.assets.equities.Equity bought.
        short_share: The tradingmachine.assets.equities.Equity sold.
        rupees_per_leg: The float amount each leg is sized to.
    """

    def __init__(self):
        """Looks both shares up.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: A share could not be found in UBI.
        """
        self.long_share = equities.Equity(exchange="nse", symbol="IDEA")
        self.short_share = equities.Equity(exchange="nse", symbol="YESBANK")
        self.rupees_per_leg = 20000.0

    def quantity_for(self, share: equities.Equity) -> int:
        """Works out how many shares make up one leg.

        Args:
            share: The tradingmachine.assets.equities.Equity to size.

        Returns:
            The int number of shares worth about `rupees_per_leg`.

        Raises:
            ValueError: UBI has no last price for the share.
        """
        last_price = share.last_price
        if last_price is None:
            raise ValueError(f"UBI has no last price for {share!r}")
        return int(self.rupees_per_leg // last_price)

    def run(self) -> None:
        """Prints the pair trade's plan.

        Returns:
            None.

        Raises:
            ValueError: UBI has no last price for one of the shares.
        """
        plan = together_part.TogetherPart(
            children=[
                order_part.OrderPart(
                    instrument=self.long_share,
                    transaction_type="buy",
                    quantity=self.quantity_for(self.long_share),
                    product="mis",
                    pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
                ),
                order_part.OrderPart(
                    instrument=self.short_share,
                    transaction_type="sell",
                    quantity=self.quantity_for(self.short_share),
                    product="mis",
                    pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
                ),
            ],
        )
        print(json.dumps(plan.document(), indent=2))


if __name__ == "__main__":
    PairTrade().run()
