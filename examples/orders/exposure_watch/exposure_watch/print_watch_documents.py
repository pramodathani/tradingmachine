"""Build the watched objects of an exposure hedge from a set of weights.

The program turns a table of weights for Vodafone Idea and Yes Bank, such as betas against the market, into exposure watches and prints the object UBI would read for each, then the watch list of an exposure hedge built from them. Nothing is sent to UBI's order routes.

Typical usage example:

  .venv/bin/python examples/orders/exposure_watch/exposure_watch/print_watch_documents.py
"""

from tradingmachine.assets import equities
from tradingmachine.orders import exposure_hedge
from tradingmachine.orders import exposure_watch


class WatchDocumentReport:
    """A report of the watched objects built from a table of weights.

    Attributes:
        weights: The dict of NSE symbol to the float exposure one share of it carries.
        watches: The list of tradingmachine.orders.exposure_watch.ExposureWatch built from the weights.
    """

    def __init__(self):
        """Builds one watch per weighted share.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: A share could not be found in UBI.
        """
        self.weights = {
            "IDEA": 1.3,
            "YESBANK": 0.9,
        }
        self.watches = []
        for symbol, weight in self.weights.items():
            share = equities.Equity(exchange="nse", symbol=symbol)
            self.watches.append(
                exposure_watch.ExposureWatch(share, exposure_per_unit=weight)
            )

    def run(self) -> None:
        """Prints each watch's object and the watch list of a hedge built from them.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for watch in self.watches:
            print(f"{watch.instrument.symbol}: {watch.document()}")
        hedge = exposure_hedge.ExposureHedgeOrder(
            self.watches[0].instrument,
            watched=self.watches,
            lower_band=-50,
            upper_band=50,
            product="mis",
        )
        print(f"Hedge watches {len(hedge.synthetic['watched'])} instruments")


if __name__ == "__main__":
    WatchDocumentReport().run()
