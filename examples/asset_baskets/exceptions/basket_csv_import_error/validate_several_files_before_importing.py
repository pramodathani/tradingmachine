"""Validate several CSV files by importing them, catching AssetBasketError for every file that is refused.

The program writes three small files that are each wrong in a different way: one gives a weight to only some rows, one has only a header, and one has no symbol column. Importing each raises BasketCsvImportError, which is caught through its base class AssetBasketError, and the program prints the reason for each file. The files are removed at the end, and nothing is saved to MongoDB, because each import stops before the basket is built.

Typical usage example:

  .venv/bin/python examples/asset_baskets/exceptions/basket_csv_import_error/validate_several_files_before_importing.py
"""

import pathlib
import tempfile

from tradingmachine.asset_baskets import basket_csv_importer
from tradingmachine.asset_baskets import exceptions


class CsvFileValidation:
    """A check of several CSV files against what the importer accepts.

    Attributes:
        importer: The tradingmachine.asset_baskets.basket_csv_importer.BasketCsvImporter that reads the files.
        files: The dict of str description to list of str lines for each file.
        directory: The pathlib.Path of the temporary directory the files are written to, or None before run.
    """

    def __init__(self):
        """Creates the importer and the contents of the files.

        Raises:
            ValueError: The shared client is not configured.
        """
        self.importer = basket_csv_importer.BasketCsvImporter()
        self.files = {
            "partial weights": [
                "symbol,weight",
                "IDEA,0.6",
                "BHARTIARTL,",
            ],
            "header only": [
                "symbol,weight",
            ],
            "no symbol column": [
                "name,weight",
                "Vodafone Idea,1.0",
            ],
        }
        self.directory = None

    def check(self, description: str, lines: list[str]) -> None:
        """Writes one file, imports it and prints the outcome.

        Args:
            description: The str description of what is wrong with the file.
            lines: The list of str lines the file holds.

        Returns:
            None.

        Raises:
            OSError: The file could not be written.
        """
        path = self.directory / f"{description.replace(' ', '_')}.csv"
        path.write_text("\n".join(lines) + "\n")
        try:
            self.importer.import_file(path, name="Never saved example basket")
        except exceptions.AssetBasketError as error:
            print(f"{description}: {type(error).__name__}: {error}")
            return
        print(f"{description}: unexpectedly imported")

    def run(self) -> None:
        """Checks every file in a temporary directory that is removed at the end.

        Returns:
            None.

        Raises:
            OSError: A file could not be written.
        """
        with tempfile.TemporaryDirectory() as directory_name:
            self.directory = pathlib.Path(directory_name)
            for description, lines in self.files.items():
                self.check(description, lines)


if __name__ == "__main__":
    CsvFileValidation().run()
