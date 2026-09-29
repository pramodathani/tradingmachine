"""Print the futures curve of a share, one line per live expiry.

The program lists every live RELIANCE futures contract on the nse, builds each one from its row, and prints its last price next to its premium over the share, so the premium can be seen growing with time to expiry.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity_futures/futures_curve.py
"""

from tradingmachine.assets import equities


class ShareFuturesCurve:
    """The live futures contracts on one share, from the soonest expiry to the latest.

    Attributes:
        underlying_symbol: The str symbol of the share, such as `RELIANCE`.
    """

    def __init__(self, underlying_symbol: str = "RELIANCE"):
        """Stores the share whose curve to print.

        Args:
            underlying_symbol: The str nse symbol of the share.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Lists the contracts and prints one line for each.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.EquityFuturesError: A listed contract could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        rows = equities.EquityFutures.contracts(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        if rows is None:
            print(f"No live futures on {self.underlying_symbol}.")
            return
        share = equities.Equity(exchange="nse", symbol=self.underlying_symbol)
        print(f"{self.underlying_symbol} share: {share.last_price}")
        for expiry_date in rows["expiry_date"]:
            contract = equities.EquityFutures(
                exchange="nse",
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
                underlying=share,
            )
            basis_percent = contract.basis_percent
            if basis_percent is None:
                premium = "unknown"
            else:
                premium = f"{basis_percent:.2f}%"
            print(f"{expiry_date}: {contract.last_price}, premium {premium}")


if __name__ == "__main__":
    ShareFuturesCurve().run()
