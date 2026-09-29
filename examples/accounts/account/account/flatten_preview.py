"""Preview what the account-wide kill switch would cancel and close.

The program asks UBI for a dry run of `Account.flatten`, which lists the open orders it would cancel and the positions it would close without sending anything, and prints a count of each followed by the details.

Typical usage example:

  .venv/bin/python examples/accounts/account/account/flatten_preview.py
"""

from tradingmachine.accounts import account


class FlattenPreview:
    """A dry run of flattening the whole trading account.

    Attributes:
        trading_account: The tradingmachine.accounts.account.Account the preview is asked for.
    """

    def __init__(self):
        """Creates the preview over the account UBI trades for.

        Raises:
            Nothing.
        """
        self.trading_account = account.Account()

    def print_items(self, heading: str, items: list) -> None:
        """Prints a heading with a count, then one line per item.

        Args:
            heading: The str heading, such as `Orders to cancel`.
            items: The list of items UBI reported, each printed as it came.

        Returns:
            None.

        Raises:
            Nothing.
        """
        print(f"{heading}: {len(items)}")
        for item in items:
            print(f"  {item}")

    def run(self) -> None:
        """Asks UBI for the dry run and prints what it would do.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        preview = self.trading_account.flatten(confirm="FLATTEN", dry_run=True)
        self.print_items("Orders to cancel", preview["would_cancel"])
        self.print_items("Positions to close", preview["would_close"])


if __name__ == "__main__":
    FlattenPreview().run()
