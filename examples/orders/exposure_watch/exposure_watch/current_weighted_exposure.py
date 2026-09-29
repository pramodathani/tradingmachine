"""Work out the weighted exposure an exposure hedge would see in the account now.

The program builds exposure watches over Vodafone Idea and Yes Bank, reads the net position held in each, and adds up quantity times exposure per unit the way UBI's exposure hedge does, printing each part and the total. It only reads positions and places no order.

Typical usage example:

  .venv/bin/python examples/orders/exposure_watch/exposure_watch/current_weighted_exposure.py
"""

from tradingmachine.assets import equities
from tradingmachine.orders import exposure_watch


class CurrentWeightedExposure:
    """The account's weighted exposure over a set of watched shares.

    Attributes:
        watches: The list of tradingmachine.orders.exposure_watch.ExposureWatch whose positions are added up.
    """

    def __init__(self):
        """Builds the watches over Vodafone Idea and Yes Bank.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: A share could not be found in UBI.
        """
        self.watches = [
            exposure_watch.ExposureWatch(
                equities.Equity(exchange="nse", symbol="IDEA"),
                exposure_per_unit=1.0,
            ),
            exposure_watch.ExposureWatch(
                equities.Equity(exchange="nse", symbol="YESBANK"),
                exposure_per_unit=0.5,
            ),
        ]

    def net_quantity(self, watch: exposure_watch.ExposureWatch) -> int:
        """Adds up the net quantity held in a watched instrument across every product.

        Args:
            watch: The tradingmachine.orders.exposure_watch.ExposureWatch to read.

        Returns:
            The int net quantity, positive when long and negative when short.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the positions.
        """
        positions = watch.instrument.net_positions
        if positions is None:
            return 0
        total = 0
        for row in positions.to_dict("records"):
            total = total + int(row["quantity"])
        return total

    def run(self) -> None:
        """Prints each watched share's exposure and the total.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not read the positions.
        """
        total = 0.0
        for watch in self.watches:
            document = watch.document()
            per_unit = document.get("exposure_per_unit", 1.0)
            quantity = self.net_quantity(watch)
            exposure = quantity * per_unit
            total = total + exposure
            print(
                f"{watch.instrument.symbol}: {quantity} held x {per_unit} = {exposure}"
            )
        print(f"Total weighted exposure: {total}")


if __name__ == "__main__":
    CurrentWeightedExposure().run()
