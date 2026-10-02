"""Build a participation order for the nearest NIFTY future and show how UBI rounds its slices down to whole lots.

The program finds the nearest NIFTY futures contract, reads its lot size, and builds an order for ten lots that takes 5% of the traded volume with at most thirty slices. Since UBI's fix of 2026-10-02, each slice is cut down to whole lots and a share under one lot waits for more volume, so the program prints what a few volumes would send. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/plan_parts/participation_execution/participation_execution/nifty_futures_in_whole_lots.py
"""

import json

from tradingmachine.assets import equities
from tradingmachine.orders.plan_parts import marketable_pricing
from tradingmachine.orders.plan_parts import order_part
from tradingmachine.orders.plan_parts import participation_execution


class NiftyFuturesParticipation:
    """A participation buy of ten lots of the nearest NIFTY future.

    Attributes:
        contract: The tradingmachine.assets.equities.EquityIndexFutures for the nearest NIFTY future.
        execution: The tradingmachine.orders.plan_parts.participation_execution.ParticipationExecution the order is sent with.
    """

    def __init__(self):
        """Finds the nearest contract and builds the execution.

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
        self.execution = participation_execution.ParticipationExecution(
            percent=5.0,
            most_slices=30,
        )

    def run(self) -> None:
        """Prints the order's object and the slices a few volumes would send.

        Returns:
            None.

        Raises:
            Nothing.
        """
        lot_size = int(self.contract.lot_size)
        part = order_part.OrderPart(
            instrument=self.contract,
            transaction_type="buy",
            quantity=10 * lot_size,
            product="nrml",
            pricing=marketable_pricing.MarketablePricing(buffer_ticks=2),
            execution=self.execution,
        )
        print(
            f"Lot size of the NIFTY future expiring {self.contract.expiry_date}: {lot_size}"
        )
        print(json.dumps(part.document(), indent=2))
        for traded_volume in [
            1000,
            2600,
            5000,
        ]:
            share = traded_volume * self.execution.percent / 100
            whole_lots = int(share) - int(share) % lot_size
            print(
                f"{traded_volume} traded gives a share of {share:.0f}, sent as {whole_lots}"
            )


if __name__ == "__main__":
    NiftyFuturesParticipation().run()
