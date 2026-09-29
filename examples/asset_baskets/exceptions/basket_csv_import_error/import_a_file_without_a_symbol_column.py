"""Import a CSV file that has no symbol column and handle the BasketCsvImportError.

BasketCsvImporter needs a `symbol` column, or an `instrument_id` one, to know which instruments a file names. The program writes a small file whose column is called `ticker`, imports it, catches BasketCsvImportError, and prints the columns the file does have. The file is removed at the end, and nothing is saved to MongoDB, because the import stops before the basket is built.

Typical usage example:

  .venv/bin/python examples/asset_baskets/exceptions/basket_csv_import_error/import_a_file_without_a_symbol_column.py
"""

import pathlib
import tempfile

from tradingmachine.asset_baskets import basket_csv_importer
from tradingmachine.asset_baskets import exceptions


class MissingColumnImport:
    """An import of a CSV file whose instrument column has the wrong name.

    Attributes:
        importer: The tradingmachine.asset_baskets.basket_csv_importer.BasketCsvImporter that reads the file.
        lines: The list of str lines the file holds.
    """

    def __init__(self):
        """Creates the importer and the file's lines.

        Raises:
            ValueError: The shared client is not configured.
        """
        self.importer = basket_csv_importer.BasketCsvImporter()
        self.lines = [
            "ticker,weight",
            "IDEA,0.5",
            "BHARTIARTL,0.5",
        ]

    def run(self) -> None:
        """Writes the file, imports it and prints why it was refused.

        Returns:
            None.

        Raises:
            OSError: The temporary file could not be written or removed.
        """
        with tempfile.NamedTemporaryFile(
            "w",
            suffix=".csv",
            delete=False,
        ) as csv_file:
            csv_file.write("\n".join(self.lines) + "\n")
            path = pathlib.Path(csv_file.name)
        try:
            basket = self.importer.import_file(path, name="Never saved example basket")
        except exceptions.BasketCsvImportError as error:
            print(f"BasketCsvImportError: {error}")
            print(f"The file's columns are: {self.lines[0]}")
            print("Rename the ticker column to symbol and import it again.")
            return
        finally:
            path.unlink()
        print(f"Unexpectedly imported {basket!r}")


if __name__ == "__main__":
    MissingColumnImport().run()
