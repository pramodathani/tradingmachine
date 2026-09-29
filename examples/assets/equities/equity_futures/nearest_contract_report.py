"""Report on the soonest futures contract on a share that still has a day to run.

The program lists the expiries of the RELIANCE futures on the nse, builds the first contract that expires after today, and prints its price, its size and how far it trades above the share.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity_futures/nearest_contract_report.py
"""

import datetime

from tradingmachine.assets import equities


class NearestShareFuturesReport:
    """A report on the soonest futures contract on one share.

    Attributes:
        underlying_symbol: The str symbol of the share, such as `RELIANCE`.
    """

    def __init__(self, underlying_symbol: str = "RELIANCE"):
        """Stores the share to report on.

        Args:
            underlying_symbol: The str nse symbol of the share.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def next_expiry(self) -> datetime.date:
        """Chooses the soonest expiry after today, so the contract still has time to run.

        Returns:
            The datetime.date of the expiry.

        Raises:
            ValueError: No futures are listed on the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        expiries = equities.EquityFutures.expiries(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        if not expiries:
            raise ValueError(f"No futures are listed on {self.underlying_symbol}")
        today = datetime.date.today()
        for expiry in expiries:
            if expiry > today:
                return expiry
        return expiries[0]

    def run(self) -> None:
        """Builds the contract and prints the report.

        Returns:
            None.

        Raises:
            ValueError: No futures are listed on the share.
            tradingmachine.assets.exceptions.EquityFuturesError: UBI has no such contract.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        contract = equities.EquityFutures(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=self.next_expiry(),
        )
        print(f"{contract.underlying_symbol} futures expiring {contract.expiry_date}")
        print(f"Days to expiry: {contract.days_to_expiry}")
        print(f"Lot size: {contract.lot_size} shares")
        print(f"Last price: {contract.last_price}")
        print(f"Contract value: {contract.contract_value}")
        print(f"Share price: {contract.underlying_price}")
        print(f"Basis: {contract.basis:.2f}")
        print(f"Basis in per cent: {contract.basis_percent:.2f}")
        print(f"Annual cost of carry: {contract.cost_of_carry:.2f}%")
        print(f"Open interest: {contract.open_interest}")


if __name__ == "__main__":
    NearestShareFuturesReport().run()
