"""Price protective Nifty puts at several distances below the index.

A protective put pays out if the index falls below its strike, like insurance on a portfolio. The program builds the puts on the next expiry at roughly 1, 2, 3 and 5 per cent below the index, through the base IndexOption class, and prints the premium of each as a percentage of the index and of one lot's notional value, with its delta.

Typical usage example:

  .venv/bin/python examples/assets/instruments/index_option/protective_put_cost.py
"""

import datetime

from tradingmachine.assets import equities
from tradingmachine.assets import instruments


class ProtectivePutCost:
    """The cost of Nifty puts at several distances out of the money.

    Attributes:
        distances_percent: A list of float distances below the index, in per cent.
    """

    def __init__(self):
        """Stores the distances to price.

        Raises:
            Nothing.
        """
        self.distances_percent = [
            1.0,
            2.0,
            3.0,
            5.0,
        ]

    def choose_expiry(self) -> datetime.date:
        """Chooses the first Nifty option expiry after today.

        Returns:
            The datetime.date of the expiry.

        Raises:
            ValueError: No expiry after today is listed.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        today = datetime.date.today()
        expiries = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        for expiry_date in expiries:
            if expiry_date > today:
                return expiry_date
        raise ValueError(f"No Nifty option expiry after today is listed: {today=}")

    def run(self) -> None:
        """Prints one line per distance.

        Returns:
            None.

        Raises:
            ValueError: No expiry after today is listed.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        expiry_date = self.choose_expiry()
        chain = equities.EquityIndexOption.chain(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiry_date,
        )
        puts = chain[chain["option_type"] == "PE"]
        level = equities.EquityIndex(exchange="nse", symbol="NIFTY").last_price
        print(f"NIFTY at {level}, puts expiring {expiry_date}")
        for distance in self.distances_percent:
            target = level * (1 - distance / 100)
            distances = (puts["strike_price"] - target).abs()
            row = puts.loc[distances.idxmin()]
            put = instruments.IndexOption(instrument_id=row["instrument_id"])
            premium = put.last_price
            greeks = put.greeks()
            delta_text = "-"
            if greeks is not None:
                delta_text = f"{greeks['delta']:.3f}"
            print(
                f"  {distance:.0f}% below: strike {put.strike_price:.0f}, "
                f"premium {premium}, {premium / level * 100:.2f}% of the index, "
                f"Rs {put.premium_per_lot:,.0f} a lot on Rs {put.notional_value:,.0f}, "
                f"delta {delta_text}"
            )


if __name__ == "__main__":
    ProtectivePutCost().run()
