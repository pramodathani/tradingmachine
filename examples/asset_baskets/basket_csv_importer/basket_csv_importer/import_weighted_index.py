"""Import a weighted index from a CSV file and compare it with the official index.

The program writes a temporary CSV file in the style of an index factsheet, with `Symbol` and `Weight` columns for five IT shares, imports it as an index linked to the NSE's NIFTY IT index under the temporary name `example-index-csv-weighted`, prints the imported weights and today's move of the basket beside the official index's, and deletes the stored copy before it ends, whatever happens.

Typical usage example:

  .venv/bin/python examples/asset_baskets/basket_csv_importer/basket_csv_importer/import_weighted_index.py
"""

import os
import tempfile

from tradingmachine.asset_baskets import asset_basket
from tradingmachine.asset_baskets import basket_csv_importer
from tradingmachine.assets import equities

NAME = "example-index-csv-weighted"

EFFECTIVE_DATE = "2026-09-01"

ROWS = [
    "Symbol,Weight",
    "INFY,28.5%",
    "TCS,24.0%",
    "HCLTECH,11.5%",
    "TECHM,9.0%",
    "WIPRO,7.0%",
]


class ImportWeightedIndex:
    """A weighted index read from a CSV file and linked to the index it describes.

    Attributes:
        importer: The tradingmachine.asset_baskets.basket_csv_importer.BasketCsvImporter that reads and stores the file.
        nifty_it: The tradingmachine.assets.equities.EquityIndex for NIFTY IT, which the basket is linked to.
    """

    def __init__(self):
        """Creates the importer and looks the official index up in UBI.

        Raises:
            tradingmachine.assets.exceptions.EquityIndexError: UBI does not know the index.
        """
        self.importer = basket_csv_importer.BasketCsvImporter()
        self.nifty_it = equities.EquityIndex(exchange="nse", symbol="NIFTYIT")

    def import_rows(self) -> asset_basket.AssetBasket:
        """Writes the rows to a temporary CSV file and imports it.

        Returns:
            The tradingmachine.asset_baskets.asset_basket.AssetBasket built from the file and stored, which is an Index.

        Raises:
            tradingmachine.asset_baskets.exceptions.AssetBasketError: The file could not be turned into a basket.
            pymongo.errors.PyMongoError: MongoDB could not be reached.
        """
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "nifty_it_weights.csv")
            with open(path, "w") as csv_file:
                for row in ROWS:
                    print(row, file=csv_file)
            return self.importer.import_file(
                path,
                name=NAME,
                kind="index",
                linked_instrument=self.nifty_it,
                effective_date=EFFECTIVE_DATE,
                source="example",
            )

    def run(self) -> None:
        """Imports the file, prints the weights and today's moves, and deletes the stored copy.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.AssetBasketError: The file could not be turned into a basket.
            pymongo.errors.PyMongoError: MongoDB could not be reached.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        basket = self.import_rows()
        try:
            print(f"Imported {basket} with {basket.weighting} weights:")
            print(basket.weights.round(3))
            print(f"Basket today: {basket.day_change_percent:+.2f}%")
            linked = basket.linked_instrument
            print(f"Linked index {linked.symbol} last at {linked.last_price}")
        finally:
            self.importer.store.delete(NAME, EFFECTIVE_DATE)


if __name__ == "__main__":
    ImportWeightedIndex().run()
