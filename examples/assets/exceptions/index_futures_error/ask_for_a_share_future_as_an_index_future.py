"""Ask for a RELIANCE future through the IndexFutures class and handle the IndexFuturesError.

IndexFutures accepts only a future on an index. The program looks a RELIANCE share future up through it, catches IndexFuturesError, and builds the same contract through the general Futures class instead.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/index_futures_error/ask_for_a_share_future_as_an_index_future.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class ShareFutureAsIndexFuture:
    """A lookup of a share future through the IndexFutures class.

    Attributes:
        exchange: The str exchange the future trades on.
        segment: The str UBI segment of share futures.
        underlying_symbol: The str symbol of the share.
    """

    def __init__(self):
        """Creates the lookup for a RELIANCE future.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.segment = "equity_futures"
        self.underlying_symbol = "RELIANCE"

    def run(self) -> None:
        """Looks the future up as an index future, catches the error and builds it as a plain future.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know the future.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date = equities.EquityFutures.expiries(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
        )[-1]
        try:
            contract = instruments.IndexFutures(
                exchange=self.exchange,
                segment=self.segment,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
            )
        except exceptions.IndexFuturesError as error:
            print(f"IndexFuturesError: {error}")
            contract = instruments.Futures(
                exchange=self.exchange,
                segment=self.segment,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
            )
        print(f"Built {contract!r}")
        print(
            f"Lot size: {contract.lot_size}, expiring in {contract.days_to_expiry} days"
        )


if __name__ == "__main__":
    ShareFutureAsIndexFuture().run()
