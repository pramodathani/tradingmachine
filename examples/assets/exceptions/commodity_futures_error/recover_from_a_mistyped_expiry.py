"""Recover from a mistyped expiry date by catching CommodityFuturesError.

The program asks for a GOLDM (gold mini) futures contract on a day no contract expires, catches CommodityFuturesError, then reads the expiries that are listed and builds the contract for the first one on or after the day asked for.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/commodity_futures_error/recover_from_a_mistyped_expiry.py
"""

import datetime

from tradingmachine.assets import commodities
from tradingmachine.assets import exceptions


class MistypedExpiryRecovery:
    """A lookup of a futures contract that falls back to a listed expiry.

    Attributes:
        exchange: The str exchange the contract trades on.
        underlying_symbol: The str symbol the contract is written on.
        wanted_expiry_date: The datetime.date the person asked for, on which no contract expires.
    """

    def __init__(self):
        """Creates the lookup with the contract the person asked for.

        Raises:
            Nothing.
        """
        self.exchange = "mcx"
        self.underlying_symbol = "GOLDM"
        self.wanted_expiry_date = datetime.date(2026, 12, 25)

    def build_contract(
        self, expiry_date: datetime.date
    ) -> commodities.CommodityFutures:
        """Looks one contract up in UBI.

        Args:
            expiry_date: The datetime.date the contract expires on.

        Returns:
            The commodities.CommodityFutures UBI knows for that expiry.

        Raises:
            tradingmachine.assets.exceptions.CommodityFuturesError: UBI has no such contract.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup.
        """
        return commodities.CommodityFutures(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )

    def listed_expiry_on_or_after(self) -> datetime.date | None:
        """Picks the listed expiry closest after the day asked for.

        Returns:
            The first listed datetime.date on or after wanted_expiry_date, or the last listed one when every expiry is earlier, or None when nothing is listed.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        listed_expiries = commodities.CommodityFutures.expiries(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
        )
        for expiry_date in listed_expiries:
            if expiry_date >= self.wanted_expiry_date:
                return expiry_date
        if listed_expiries:
            return listed_expiries[-1]
        return None

    def run(self) -> None:
        """Asks for the mistyped contract, recovers from the error and prints the contract found.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        try:
            contract = self.build_contract(self.wanted_expiry_date)
        except exceptions.CommodityFuturesError as error:
            print(f"CommodityFuturesError: {error}")
            listed_expiry = self.listed_expiry_on_or_after()
            if listed_expiry is None:
                print(
                    f"No {self.underlying_symbol} contract is listed on the {self.exchange}, which is expected for a mistyped name."
                )
                return
            print(f"Using the listed expiry {listed_expiry} instead.")
            contract = self.build_contract(listed_expiry)
        print(f"Contract: {contract!r}")
        print(f"Expires on {contract.expiry_date}, in {contract.days_to_expiry} days")
        print(f"Lot size: {contract.lot_size}")


if __name__ == "__main__":
    MistypedExpiryRecovery().run()
