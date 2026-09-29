"""Print the expiry calendar of Nifty options and Reliance futures.

The program lists the live expiries of each underlying, builds one contract for each expiry, and prints how many days it has left, whether it is a weekly or a monthly expiry, and the expiry it would roll to. These are the members every Derivative shares, whatever its family.

Typical usage example:

  .venv/bin/python examples/assets/instruments/derivative/expiry_calendar.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import instruments


class ExpiryCalendar:
    """A calendar of the next few expiries of an index option and a stock future.

    Attributes:
        expiry_count: The int number of expiries to show for each underlying.
    """

    def __init__(self, expiry_count: int = 4):
        """Stores how many expiries to show.

        Args:
            expiry_count: The int number of expiries to show for each underlying.

        Raises:
            Nothing.
        """
        self.expiry_count = expiry_count

    def print_contract(self, contract: instruments.Derivative) -> None:
        """Prints one line about one contract.

        Args:
            contract: The tradingmachine.assets.instruments.Derivative to describe.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        print(
            f"  {contract.expiry_date}  {contract.days_to_expiry:>4} days  "
            f"{contract.expiry_kind:<8} rolls to {contract.next_expiry}"
        )

    def nifty_options(self) -> None:
        """Prints the calendar of Nifty options, building one option from each expiry's chain.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        print("NIFTY options:")
        expiries = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        for expiry_date in expiries[: self.expiry_count]:
            chain = equities.EquityIndexOption.chain(
                exchange="nse",
                underlying_symbol="NIFTY",
                expiry_date=expiry_date,
            )
            first_row = chain.iloc[0]
            option = instruments.IndexOption(instrument_id=first_row["instrument_id"])
            self.print_contract(option)

    def reliance_futures(self) -> None:
        """Prints the calendar of Reliance futures.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        print("RELIANCE futures:")
        expiries = equities.EquityFutures.expiries(
            exchange="nse",
            underlying_symbol="RELIANCE",
        )
        for expiry_date in expiries[: self.expiry_count]:
            future = equities.EquityFutures(
                exchange="nse",
                underlying_symbol="RELIANCE",
                expiry_date=expiry_date,
            )
            self.print_contract(future)

    def run(self) -> None:
        """Prints both calendars.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        self.nifty_options()
        self.reliance_futures()


if __name__ == "__main__":
    ExpiryCalendar().run()
