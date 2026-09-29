"""Report the trading activity in the soonest Nifty futures contract after today.

The program builds the Nifty futures contract with the soonest expiry after today and prints its order book, its volume, its average traded price and how its open interest has ranged during the day.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity_index_futures/open_interest_report.py
"""

import datetime

from tradingmachine.assets import equities


class IndexFuturesActivityReport:
    """A report on the trading activity in one equity index futures contract.

    Attributes:
        contract: The tradingmachine.assets.equities.EquityIndexFutures the report describes.
    """

    def __init__(self, underlying_symbol: str = "NIFTY"):
        """Builds the contract with the soonest expiry after today.

        Args:
            underlying_symbol: The str nse symbol of the index, such as `NIFTY`.

        Raises:
            ValueError: No futures are listed on the index.
            tradingmachine.assets.exceptions.EquityIndexFuturesError: UBI has no such contract.
        """
        expiries = equities.EquityIndexFutures.expiries(
            exchange="nse",
            underlying_symbol=underlying_symbol,
        )
        if not expiries:
            raise ValueError(f"No futures are listed on {underlying_symbol}")
        expiry_date = expiries[-1]
        today = datetime.date.today()
        for expiry in expiries:
            if expiry > today:
                expiry_date = expiry
                break
        self.contract = equities.EquityIndexFutures(
            exchange="nse",
            underlying_symbol=underlying_symbol,
            expiry_date=expiry_date,
        )

    def run(self) -> None:
        """Prints the order book and the day's activity.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        contract = self.contract
        print(f"{contract.underlying_symbol} futures expiring {contract.expiry_date}")
        print(f"Kind of expiry: {contract.expiry_kind}")
        print(f"Lot size: {contract.lot_size}")
        print(f"Best bid: {contract.best_bid}")
        print(f"Best offer: {contract.best_offer}")
        print(f"Mid price: {contract.mid_price}")
        print(f"Average traded price: {contract.volume_weighted_average_price}")
        print(f"Volume: {contract.total_traded_volume}")
        print(f"Open interest: {contract.open_interest}")
        print(f"Open interest day high: {contract.open_interest_day_high}")
        print(f"Open interest day low: {contract.open_interest_day_low}")
        print(f"Last trade: {contract.last_trade_time}")


if __name__ == "__main__":
    IndexFuturesActivityReport().run()
