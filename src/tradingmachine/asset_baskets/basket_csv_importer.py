"""Fills the basket store from a CSV file.

`BasketCsvImporter.import_file` reads a CSV with a `symbol` column and, optionally, `exchange`, `segment`, `weight`, `quantity` and `instrument_id` columns, looks every row's instrument up in UBI in one list request, builds the basket as the class its `kind` names, and saves it through `tradingmachine.asset_baskets.basket_store.BasketStore`. Column names are read without regard to case or surrounding spaces, so the constituent files the NSE publishes, whose header has `Symbol`, import as they are. A row without an exchange or a segment takes the ones given to `import_file`.

A file without a `weight` column makes an equally weighted index, recorded with `weighting` set to `equal`, because the NSE's free constituent files carry no weights. Weights may be fractions or percentages, since every basket normalises them. Scripts that download constituents and weights, to be kept in `bin/`, are meant to call this same importer.

Typical usage example:

  importer = basket_csv_importer.BasketCsvImporter()
  nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
  basket = importer.import_file(
      "ind_nifty50list.csv",
      name="NIFTY",
      kind="index",
      linked_instrument=nifty,
      effective_date="2026-09-30",
  )
"""

import datetime
import pathlib

import pandas as pd

from tradingmachine.asset_baskets import asset_basket
from tradingmachine.asset_baskets import basket_store
from tradingmachine.asset_baskets import exceptions
from tradingmachine.asset_baskets import index
from tradingmachine.assets import instruments
from tradingmachine.unified_broker_interface import client
from tradingmachine.utilities import configuration

REQUIRED_COLUMN = "symbol"

NUMBER_COLUMNS = [
    "weight",
    "quantity",
]


class BasketCsvImporter:
    """A reader of CSV files into stored baskets.

    Attributes:
        store: The basket_store.BasketStore the imported baskets are saved to.
    """

    def __init__(
        self,
        project_configuration: configuration.Configuration | None = None,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Initialises the importer with the store it saves to.

        Args:
            project_configuration: The configuration.Configuration to read the MongoDB settings from, or None to build one that reads the environment and the `.env` file.
            unified_broker_interface: The client.UnifiedBrokerInterface to look instruments up through, or None to share the one every instrument uses.

        Raises:
            ValueError: No client was given and the shared client is not configured.
        """
        self.store = basket_store.BasketStore(
            project_configuration=project_configuration,
            unified_broker_interface=unified_broker_interface,
        )

    def import_file(
        self,
        path: str | pathlib.Path,
        name: str,
        kind: str = index.Index.KIND,
        exchange: str = "nse",
        segment: str = "equities",
        linked_instrument: instruments.Instrument | None = None,
        effective_date: datetime.date | str | None = None,
        unmapped_weight: float = 0.0,
        source: str = "csv",
    ) -> asset_basket.AssetBasket:
        """Reads a CSV file, builds the basket it describes and saves it.

        Args:
            path: The str or pathlib.Path of the CSV file.
            name: The str name to store the basket under, such as `NIFTY`.
            kind: The str kind of basket to build, such as `index`, `portfolio` or `mutual_fund_constituents`.
            exchange: The str exchange of any row that does not give one.
            segment: The str segment of any row that does not give one, such as `equities`.
            linked_instrument: The tradingmachine.assets.instruments.Instrument whose contents the file describes, such as the NIFTY index, or None.
            effective_date: The first day the basket is in effect as a datetime.date or a `YYYY-MM-DD` str, or None for today.
            unmapped_weight: The float share of a fund, between 0 and 1, held outside the listed instruments.
            source: The str name of where the file came from, stored with the basket.

        Returns:
            The asset_basket.AssetBasket that was built and saved.

        Raises:
            BasketCsvImportError: The file has no `symbol` column, has no rows, or gives a weight or quantity to only some rows.
            BasketMemberError: UBI could not find one or more of the instruments, all of which the message lists.
            AssetBasketError: kind is not one the store knows.
            FileNotFoundError: The file does not exist.
            pymongo.errors.PyMongoError: MongoDB could not be reached or refused the write.
        """
        frame = pd.read_csv(path, dtype=str, skipinitialspace=True)
        frame.columns = [str(column).strip().lower() for column in frame.columns]
        if (
            REQUIRED_COLUMN not in frame.columns
            and "instrument_id" not in frame.columns
        ):
            raise exceptions.BasketCsvImportError(
                f"The file has no {REQUIRED_COLUMN} column: {path}"
            )
        rows = self._rows_from(frame, exchange, segment, path)
        weighting = index.STATED_WEIGHTING
        if rows[0].get("weight") is None:
            weighting = index.EQUAL_WEIGHTING
        document = {
            "name": name,
            "kind": kind,
            "unmapped_weight": unmapped_weight,
            "weighting": weighting,
            "members": rows,
        }
        basket = self.store.build(document, linked_instrument=linked_instrument)
        self.store.save(basket, effective_date=effective_date, source=source)
        return basket

    def _rows_from(
        self,
        frame: pd.DataFrame,
        exchange: str,
        segment: str,
        path: str | pathlib.Path,
    ) -> list[dict]:
        """Turns the CSV's rows into rows that name instruments.

        Args:
            frame: The pandas.DataFrame read from the file, with lower-case column names and every value as text.
            exchange: The str exchange of any row that does not give one.
            segment: The str segment of any row that does not give one.
            path: The str or pathlib.Path of the file, for error messages.

        Returns:
            A list of dicts, one per row with a symbol or an instrument id, each with `symbol`, `exchange` and `segment` or `instrument_id`, and `weight` and `quantity` as floats when the file has them.

        Raises:
            BasketCsvImportError: The file has no rows, or gives a weight or quantity to only some rows.
        """
        rows = []
        for record in frame.to_dict(orient="records"):
            row = {}
            symbol = self._text(record.get(REQUIRED_COLUMN))
            instrument_id = self._text(record.get("instrument_id"))
            if symbol is None and instrument_id is None:
                continue
            if instrument_id is not None:
                row["instrument_id"] = instrument_id
            row["symbol"] = symbol
            row["exchange"] = self._text(record.get("exchange")) or exchange
            row["segment"] = self._text(record.get("segment")) or segment
            for column in NUMBER_COLUMNS:
                value = self._text(record.get(column))
                if value is None:
                    row[column] = None
                else:
                    row[column] = float(value.replace(",", "").rstrip("%"))
            rows.append(row)
        if not rows:
            raise exceptions.BasketCsvImportError(f"The file has no rows: {path}")
        for column in NUMBER_COLUMNS:
            given_count = 0
            for row in rows:
                if row[column] is not None:
                    given_count += 1
            if 0 < given_count < len(rows):
                raise exceptions.BasketCsvImportError(
                    f"Only {given_count} of {len(rows)} rows give a {column}: {path}"
                )
        return rows

    @staticmethod
    def _text(value) -> str | None:
        """Cleans one CSV value, treating an empty cell as missing.

        Args:
            value: The cell's value, a str or a missing value such as None or NaN.

        Returns:
            The str value without surrounding spaces, or None when the cell is empty.

        Raises:
            Nothing.
        """
        if value is None or pd.isna(value):
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned
