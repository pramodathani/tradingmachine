"""Look a bond up by its ISIN and report what UBI knows about it.

The program searches the nse's fixed income segment for the start of an ISIN, builds the first bond it finds, and prints its identity and the brokers that carry it. It then shows the two gaps in UBI's coverage of bonds: there is no quote, which is reported as an error the program catches, and there are no candles.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income/bond_lookup_report.py
"""

from tradingmachine.assets import fixed_income
from tradingmachine.unified_broker_interface import exceptions


class BondLookupReport:
    """A report on one bond found by the start of its ISIN.

    Attributes:
        isin_prefix: The str the bond's ISIN must contain, such as `IN0001`.
    """

    def __init__(self, isin_prefix: str = "IN0001"):
        """Stores the part of the ISIN to search for.

        Args:
            isin_prefix: The str the bond's ISIN must contain.

        Raises:
            Nothing.
        """
        self.isin_prefix = isin_prefix

    def run(self) -> None:
        """Finds the bond and prints the report.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.FixedIncomeError: The bond found could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        matches = fixed_income.FixedIncome.search(
            exchange="nse",
            term=self.isin_prefix,
        )
        if matches is None:
            print(f"No nse bond has an ISIN containing {self.isin_prefix}.")
            return
        isin = matches["symbol"].iloc[0]
        bond = fixed_income.FixedIncome(exchange="nse", symbol=isin)
        print(f"ISIN: {bond.symbol}")
        print(f"Instrument id: {bond.instrument_id}")
        print(f"Segment: {bond.segment}")
        print(f"Lot size: {bond.lot_size}")
        brokers = []
        for mapping in bond.carried_by:
            brokers.append(mapping["broker"])
        print(f"Carried by: {', '.join(brokers)}")
        try:
            print(f"Last price: {bond.last_price}")
        except exceptions.ServiceUnavailableError as error:
            print(f"No quote: {error}")
        print(f"Candles for the last month: {bond.prices(days=30)}")
        holding = bond.holdings
        if holding is None:
            print("The account holds none of this bond.")
        else:
            print(f"Held: {holding['quantity']} units")


if __name__ == "__main__":
    BondLookupReport().run()
