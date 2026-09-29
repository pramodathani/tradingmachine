"""Import a plain list of symbols, as the NSE publishes it, into an equally weighted index.

The program writes a temporary CSV file shaped like the NSE's free constituent lists, with a `Symbol` column and no weights, imports it under the temporary name `example-index-csv-equal`, shows that it was stored with equal weights, loads it back from MongoDB, prints its level of 100 over the last month, and deletes the stored copy before it ends, whatever happens.

Typical usage example:

  .venv/bin/python examples/asset_baskets/basket_csv_importer/basket_csv_importer/import_equal_weighted_list.py
"""

import os
import tempfile

from tradingmachine.asset_baskets import basket_csv_importer

NAME = "example-index-csv-equal"

EFFECTIVE_DATE = "2026-09-01"

ROWS = [
    "Company Name,Industry,Symbol,Series,ISIN Code",
    "HDFC Bank Ltd.,Financial Services,HDFCBANK,EQ,INE040A01034",
    "ICICI Bank Ltd.,Financial Services,ICICIBANK,EQ,INE090A01021",
    "Axis Bank Ltd.,Financial Services,AXISBANK,EQ,INE238A01034",
    "State Bank of India,Financial Services,SBIN,EQ,INE062A01020",
]


class ImportEqualWeightedList:
    """An equally weighted index read from a list of symbols without weights.

    Attributes:
        importer: The tradingmachine.asset_baskets.basket_csv_importer.BasketCsvImporter that reads and stores the file.
    """

    def __init__(self):
        """Creates the importer.

        Raises:
            ValueError: The shared UBI client is not configured.
        """
        self.importer = basket_csv_importer.BasketCsvImporter()

    def write_file(self, directory: str) -> str:
        """Writes the rows to a CSV file.

        Args:
            directory: The str path of the directory to write the file in.

        Returns:
            The str path of the file written.

        Raises:
            OSError: The file could not be written.
        """
        path = os.path.join(directory, "ind_banks_list.csv")
        with open(path, "w") as csv_file:
            for row in ROWS:
                print(row, file=csv_file)
        return path

    def run(self) -> None:
        """Imports the file, loads it back, prints its level, and deletes the stored copy.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.AssetBasketError: The file could not be turned into a basket.
            pymongo.errors.PyMongoError: MongoDB could not be reached.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_file(directory)
            basket = self.importer.import_file(
                path,
                name=NAME,
                effective_date=EFFECTIVE_DATE,
                source="example",
            )
        try:
            print(f"Imported {basket} with {basket.weighting} weights")
            loaded = self.importer.store.load(NAME)
            print(f"Loaded back: {loaded}, weights {loaded.weights.round(2).to_dict()}")
            frame = loaded.prices(days=30)
            print(frame[["datetime", "close"]].tail().round(2))
        finally:
            self.importer.store.delete(NAME, EFFECTIVE_DATE)


if __name__ == "__main__":
    ImportEqualWeightedList().run()
