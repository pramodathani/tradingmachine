"""Report the synthetic and held orders the order engine is working across the whole account.

The program reads the account's open parents once and prints how many there are of each synthetic order type and in each state.

Typical usage example:

  .venv/bin/python examples/accounts/account/account/open_parents_report.py
"""

from tradingmachine.accounts import account


class OpenParentsReport:
    """A report of the open parents in the whole trading account.

    Attributes:
        trading_account: The tradingmachine.accounts.account.Account the report reads.
    """

    def __init__(self):
        """Creates the report over the account UBI trades for.

        Raises:
            Nothing.
        """
        self.trading_account = account.Account()

    def run(self) -> None:
        """Reads the open parents and prints a count by type and by state.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        parents = self.trading_account.parents
        if parents is None:
            print("The order engine is not working any parent.")
            return
        print(f"Open parents: {len(parents)}")
        print(parents["synthetic_type"].value_counts())
        print(parents["state"].value_counts())


if __name__ == "__main__":
    OpenParentsReport().run()
