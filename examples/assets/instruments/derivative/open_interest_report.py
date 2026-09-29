"""Report the open interest and contract value of the nearest index futures.

The program builds the nearest future on each of three indices and prints its underlying's level, its open interest now and its range today in lots, and what one lot is worth at the last price.

Typical usage example:

  .venv/bin/python examples/assets/instruments/derivative/open_interest_report.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import instruments


class OpenInterestReport:
    """A report of open interest across the nearest index futures.

    Attributes:
        futures: A list of tradingmachine.assets.instruments.Derivative, the nearest future on each index.
    """

    def __init__(self):
        """Builds the nearest future on each index.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup.
        """
        symbols = [
            "NIFTY",
            "BANKNIFTY",
            "FINNIFTY",
        ]
        self.futures = []
        for symbol in symbols:
            expiries = equities.EquityIndexFutures.expiries(
                exchange="nse",
                underlying_symbol=symbol,
            )
            future = equities.EquityIndexFutures(
                exchange="nse",
                underlying_symbol=symbol,
                expiry_date=expiries[0],
            )
            self.futures.append(future)

    def in_lots(self, units: int | None, contract: instruments.Derivative) -> str:
        """Turns a count of underlying units into lots for printing.

        Args:
            units: The int number of underlying units, or None when unknown.
            contract: The tradingmachine.assets.instruments.Derivative whose lot size to divide by.

        Returns:
            The str number of lots, or a dash when either figure is unknown.

        Raises:
            Nothing.
        """
        if units is None or not contract.lot_size:
            return "-"
        return f"{units // contract.lot_size:,}"

    def run(self) -> None:
        """Prints one block per future.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        for future in self.futures:
            print(f"{future.underlying_symbol} {future.expiry_date}:")
            print(f"  underlying at {future.underlying_price}")
            print(f"  open interest {self.in_lots(future.open_interest, future)} lots")
            low = self.in_lots(future.open_interest_day_low, future)
            high = self.in_lots(future.open_interest_day_high, future)
            print(f"  today's range {low} to {high} lots")
            contract_value = future.contract_value
            if contract_value is None:
                print("  one lot: unknown")
            else:
                print(f"  one lot of {future.lot_size} worth Rs {contract_value:,.0f}")


if __name__ == "__main__":
    OpenInterestReport().run()
