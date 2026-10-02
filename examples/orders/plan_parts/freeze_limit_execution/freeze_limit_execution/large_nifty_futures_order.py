"""Build a NIFTY futures order larger than the exchange's freeze quantity, split by UBI at one broker.

The program finds the nearest NIFTY futures contract and builds a buy of 40 lots two ticks past the offer with `FreezeLimitExecution`. UBI chooses the broker first, compares the quantity with that broker's published freeze quantity in the broker's own units, and sends equal orders each within it, all at once to that broker; more than 20 slices is refused and a broker that publishes none gets the order whole. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/freeze_limit_execution/freeze_limit_execution/large_nifty_futures_order.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import freeze_limit_execution
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part


class LargeFuturesOrder:
    """A forty-lot NIFTY futures buy split below the freeze quantity.

    Attributes:
        contract: The tradingmachine.assets.equities.EquityIndexFutures for the nearest NIFTY future.
    """

    def __init__(self):
        """Finds the nearest contract.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: The contract could not be found in UBI.
        """
        expiries = equities.EquityIndexFutures.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        self.contract = equities.EquityIndexFutures(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiries[0],
        )

    def run(self) -> None:
        """Prints the order's object.

        Returns:
            None.

        Raises:
            Nothing.
        """
        lot_size = int(self.contract.lot_size)
        part = order_part.OrderPart(
            instrument=self.contract,
            transaction_type="buy",
            quantity=40 * lot_size,
            product="nrml",
            pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
            execution=freeze_limit_execution.FreezeLimitExecution(),
        )
        print(
            f"NIFTY future expiring {self.contract.expiry_date}: 40 lots of {lot_size}"
        )
        print(json.dumps(part.document(), indent=2))


if __name__ == "__main__":
    LargeFuturesOrder().run()
