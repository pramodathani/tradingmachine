"""Report the account's long-term holdings as one portfolio.

The program builds a portfolio from the holdings UBI reports across every broker and prints each holding's quantity, value and weight, then the portfolio's total value, what was paid for it, its unrealised profit, and today's profit and move. It only reads; nothing is traded.

Typical usage example:

  .venv/bin/python examples/asset_baskets/portfolio/portfolio/holdings_report.py
"""

import pandas as pd

from tradingmachine.asset_baskets import exceptions
from tradingmachine.asset_baskets import portfolio


class HoldingsReport:
    """A report on the account's holdings, read as a portfolio.

    Attributes:
        held: The tradingmachine.asset_baskets.portfolio.Portfolio of the holdings, or None when the account holds nothing.
    """

    def __init__(self):
        """Reads the holdings from UBI and builds the portfolio.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        try:
            self.held = portfolio.Portfolio.from_holdings()
        except exceptions.BasketMemberError as error:
            print(f"No portfolio: {error}")
            self.held = None

    def print_table(self) -> None:
        """Prints each holding's quantity, value and weight.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: A holding has no last price.
        """
        table = pd.DataFrame(
            {
                "quantity": self.held.quantities,
                "value": self.held.values,
                "weight": self.held.weights,
            }
        )
        print(table.round(3))

    def print_totals(self) -> None:
        """Prints the portfolio's value, cost, unrealised profit and today's result.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        print(f"Value:             {self.rounded(self.held.value)}")
        print(f"Invested:          {self.rounded(self.held.invested_value)}")
        print(f"Unrealised profit: {self.rounded(self.held.unrealized_pnl)}")
        print(f"Today's profit:    {self.rounded(self.held.day_pnl)}")
        print(f"Today's move (%):  {self.rounded(self.held.day_change_percent)}")

    def rounded(self, amount: float | None) -> float | None:
        """Rounds an amount to two decimal places for printing, keeping None as it is.

        Args:
            amount: The float amount, or None when it is unknown.

        Returns:
            The float amount rounded to two decimal places, or None.

        Raises:
            Nothing.
        """
        if amount is None:
            return None
        return round(amount, 2)

    def run(self) -> None:
        """Prints the table and the totals, or nothing more when there are no holdings.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        if self.held is None:
            return
        print(f"{self.held.size} holdings")
        self.print_table()
        self.print_totals()


if __name__ == "__main__":
    HoldingsReport().run()
