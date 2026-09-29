"""Print the four price transforms side by side for a share's last trading days.

The program reads a month of Infosys daily candles through each of the four methods that `PriceTransforms` gives every instrument, and prints a table of the close, the average price, the median price, the typical price and the weighted close for the last ten days.

Typical usage example:

  .venv/bin/python examples/assets/analysis/price_transforms/price_transforms/price_transform_table.py
"""

from tradingmachine.assets import equities


class PriceTransformTable:
    """A table of the four one-number summaries of each candle.

    Attributes:
        share: The tradingmachine.assets.equities.Equity whose candles are summarised.
        rows: The int number of most recent days printed.
    """

    def __init__(self, rows: int = 10):
        """Creates the table over the Infosys share.

        Args:
            rows: The int number of most recent days printed.

        Raises:
            Nothing.
        """
        self.share = equities.Equity(exchange="nse", symbol="INFY")
        self.rows = rows

    def run(self) -> None:
        """Reads the four transforms and prints them for the last days.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        frame = self.share.average_price(days=30)
        if frame is None:
            print("UBI has no Infosys candles for the range.")
            return
        frame["med_price"] = self.share.median_price(days=30)["med_price"]
        frame["typ_price"] = self.share.typical_price(days=30)["typ_price"]
        frame["wght_close"] = self.share.weighted_close(days=30)["wght_close"]
        columns = [
            "datetime",
            "close",
            "avg_price",
            "med_price",
            "typ_price",
            "wght_close",
        ]
        table = frame[columns].tail(self.rows).copy()
        table["datetime"] = table["datetime"].dt.date
        print(table.round(2).to_string(index=False))


if __name__ == "__main__":
    PriceTransformTable().run()
