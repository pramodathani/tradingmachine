"""
Shared machinery for downloading a broker's daily instrument master file and landing it in TimescaleDB.

Each broker subclasses BrokerInstruments and implements download(). Everything else, the cleaning steps and the database write, is supplied here.
"""

import re

import pandas
from sqlalchemy import create_engine, text

from utilities.configuration import postgres_configuration

SCHEMA_NAME = "instruments"

GARBAGE_SYMBOL_PATTERNS = [
    "NSETEST",
]


class BrokerInstruments:
    """
    Base class for one broker's instrument master ingestion.

    Subclasses set BROKER_NAME and implement download(). The table written to is always SCHEMA_NAME.BROKER_NAME, created beforehand by the DDL files under data/sql/ddl.

    Attributes:
        BROKER_NAME (str): Lowercase broker name, also the table name inside the instruments schema.
        DEDUPE_KEY_COLUMNS (list[str]): Normalised column names forming this broker's natural key. An empty list disables de-duplication.
        DEDUPE_SORT_COLUMN (str | None): Column to sort by before de-duplicating, so the kept row is predictable rather than arbitrary.
    """

    BROKER_NAME = ""
    DEDUPE_KEY_COLUMNS = []
    DEDUPE_SORT_COLUMN = None

    def __init__(self):
        """
        Build the broker ingester and its database engine.

        Raises:
            NotImplementedError: If the subclass did not set BROKER_NAME.
        """
        if not self.BROKER_NAME:
            raise NotImplementedError(f"{type(self).__name__} must set BROKER_NAME")
        self.engine = create_engine(postgres_configuration["connection_string"])

    def download(self):
        """
        Fetch this broker's instrument master file or files.

        Subclasses must override this. Every file is read as text so that no value is coerced on the way in.

        Returns:
            pandas.DataFrame: One frame holding every row the broker published, already concatenated if the broker ships several files.

        Raises:
            NotImplementedError: Always, unless the subclass overrides this method.
        """
        raise NotImplementedError(f"{type(self).__name__} must implement download()")

    def normalize_columns(self, frame):
        """
        Rewrite the column names into a stable lowercase form usable as a SQL identifier.

        Some brokers bake stray whitespace and punctuation into the header itself rather than it being a parsing artifact, so the raw name is not safe to key on.

        Args:
            frame (pandas.DataFrame): Frame whose column names are to be normalised.

        Returns:
            pandas.DataFrame: A copy of the frame with normalised column names.
        """
        def clean(name):
            name = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip())
            return name.strip("_").lower()

        frame = frame.copy()
        frame.columns = [clean(column) for column in frame.columns]
        return frame

    def strip_whitespace(self, frame):
        """
        Remove leading and trailing whitespace from every text column.

        Brokers intermittently pad text fields, so the same value can arrive padded one day and bare the next.

        Args:
            frame (pandas.DataFrame): Frame to strip.

        Returns:
            pandas.DataFrame: A copy of the frame with text values stripped.
        """
        frame = frame.copy()
        for column in frame.columns:
            if frame[column].dtype == object:
                frame[column] = frame[column].str.strip()
        return frame

    def drop_unnamed_columns(self, frame):
        """
        Drop the empty placeholder columns created when a source file ends every line with a trailing delimiter.

        A column is only dropped when it is empty on every row. One carrying real values is kept and reported instead, so no data is discarded silently.

        Args:
            frame (pandas.DataFrame): Frame to examine.

        Returns:
            pandas.DataFrame: A copy of the frame without the empty placeholder columns.
        """
        frame = frame.copy()
        for column in [c for c in frame.columns if re.match(r"^unnamed(_\d+)?$", c)]:
            populated = frame[column].notna() & (frame[column].astype(str).str.strip() != "")
            if populated.any():
                print(f"{self.BROKER_NAME}: column '{column}' looks like a parsing artifact but holds {int(populated.sum())} value(s), keeping it.")
                continue
            frame = frame.drop(columns=[column])
            print(f"{self.BROKER_NAME}: dropped empty artifact column '{column}'.")
        return frame

    def drop_garbage_rows(self, frame):
        """
        Drop the placeholder instruments some brokers ship in their master files.

        These are exchange test scrips such as NSETEST, never real tradeable securities.

        Args:
            frame (pandas.DataFrame): Frame to filter.

        Returns:
            pandas.DataFrame: A copy of the frame without the placeholder rows.
        """
        if frame.empty:
            return frame
        matches = pandas.Series(False, index=frame.index)
        for column in frame.columns:
            if frame[column].dtype == object:
                for pattern in GARBAGE_SYMBOL_PATTERNS:
                    matches = matches | frame[column].astype(str).str.contains(pattern, case=False, na=False)
        dropped = int(matches.sum())
        if dropped:
            print(f"{self.BROKER_NAME}: dropped {dropped} placeholder row(s) matching {GARBAGE_SYMBOL_PATTERNS}.")
        return frame[~matches].reset_index(drop=True)

    def dedupe(self, frame):
        """
        Drop rows repeating this broker's natural key.

        Args:
            frame (pandas.DataFrame): Frame to de-duplicate.

        Returns:
            pandas.DataFrame: A copy of the frame with one row per natural key.
        """
        if not self.DEDUPE_KEY_COLUMNS:
            return frame
        if self.DEDUPE_SORT_COLUMN and self.DEDUPE_SORT_COLUMN in frame.columns:
            frame = frame.sort_values(by=self.DEDUPE_SORT_COLUMN, kind="stable", key=lambda column: column.astype(str))
        before = len(frame)
        frame = frame.drop_duplicates(subset=self.DEDUPE_KEY_COLUMNS, keep="first").reset_index(drop=True)
        dropped = before - len(frame)
        if dropped:
            print(f"{self.BROKER_NAME}: dropped {dropped} duplicate row(s) on {self.DEDUPE_KEY_COLUMNS}.")
        return frame

    def table_columns(self):
        """
        The column names of this broker's table as it currently exists in the database.

        Returns:
            list[str]: Column names in the order the table declares them.

        Raises:
            ValueError: If the table does not exist yet.
        """
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table "
                    "ORDER BY ordinal_position"
                ),
                {
                    "schema": SCHEMA_NAME,
                    "table": self.BROKER_NAME,
                },
            ).all()
        if not rows:
            raise ValueError(f"Table {SCHEMA_NAME}.{self.BROKER_NAME} does not exist. Run 'python3 -m data.create_tables' first.")
        return [row[0] for row in rows]

    def has_data_for(self, download_date):
        """
        Whether this broker's table already holds a snapshot for a given date.

        Args:
            download_date (datetime.date): The snapshot date to look for.

        Returns:
            bool: True when at least one row carries that download date.
        """
        with self.engine.connect() as connection:
            exists = connection.execute(
                text("SELECT to_regclass(:qualified_name) IS NOT NULL"),
                {"qualified_name": f"{SCHEMA_NAME}.{self.BROKER_NAME}"},
            ).scalar()
            if not exists:
                return False
            row = connection.execute(
                text(f"SELECT 1 FROM {SCHEMA_NAME}.{self.BROKER_NAME} WHERE download_date = :download_date LIMIT 1"),
                {"download_date": download_date},
            ).first()
        return row is not None

    def ingest(self, download_date=None, bootstrap=False):
        """
        Download, clean and store one day's instrument master for this broker.

        Re-running for a date already stored is a no-op unless bootstrap is set, so the daily cron job is safe to run twice.

        Args:
            download_date (datetime.date | None): Snapshot date to record. Defaults to today.
            bootstrap (bool): When True, replace that date's stored rows rather than skipping.

        Returns:
            int: The number of rows written.

        Raises:
            ValueError: If the broker's file carries a column the table does not have, which would otherwise lose data silently.
        """
        download_date = download_date or pandas.Timestamp.today().date()
        already_stored = self.has_data_for(download_date)
        if already_stored and not bootstrap:
            print(f"{self.BROKER_NAME}: already ingested for {download_date}, skipping.")
            return 0

        print(f"{self.BROKER_NAME}: downloading instruments for {download_date} ...")
        frame = self.download()
        frame = self.normalize_columns(frame)
        frame = self.strip_whitespace(frame)
        frame = self.drop_unnamed_columns(frame)
        frame = self.drop_garbage_rows(frame)
        frame = self.dedupe(frame)
        frame["download_date"] = download_date

        unknown_columns = [column for column in frame.columns if column not in self.table_columns()]
        if unknown_columns:
            raise ValueError(
                f"{self.BROKER_NAME}: the downloaded file carries column(s) {unknown_columns} that "
                f"{SCHEMA_NAME}.{self.BROKER_NAME} does not have. Add them to the DDL rather than dropping them."
            )

        if already_stored:
            with self.engine.begin() as connection:
                deleted = connection.execute(
                    text(f"DELETE FROM {SCHEMA_NAME}.{self.BROKER_NAME} WHERE download_date = :download_date"),
                    {"download_date": download_date},
                ).rowcount
            print(f"{self.BROKER_NAME}: removed {deleted} existing row(s) for {download_date} before re-ingesting.")

        frame.to_sql(self.BROKER_NAME, self.engine, schema=SCHEMA_NAME, if_exists="append", index=False, chunksize=10000)
        print(f"{self.BROKER_NAME}: ingested {len(frame)} row(s) for {download_date}.")
        return len(frame)

    def check_row_count_deviation(self, download_date, threshold=0.10):
        """
        Compare a day's row count against the average of every earlier day.

        A large swing usually means the broker's file came back truncated or unexpectedly bloated. This reports the finding and never raises, because a deviation is a signal to investigate rather than a failure.

        Args:
            download_date (datetime.date): The snapshot date to check.
            threshold (float): Allowed fractional deviation, so 0.10 permits ten percent either way.

        Returns:
            dict: Keys 'broker', 'alarm' and 'message', plus the counts behind the verdict when a comparison was possible.
        """
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(f"SELECT download_date, count(*) AS row_count FROM {SCHEMA_NAME}.{self.BROKER_NAME} GROUP BY download_date")
            ).all()

        counts_by_date = {row[0]: row[1] for row in rows}
        current_rows = counts_by_date.get(download_date)
        if current_rows is None:
            message = f"INFO: {self.BROKER_NAME}: no rows stored for {download_date}, nothing to check."
            print(message)
            return {"broker": self.BROKER_NAME, "alarm": False, "message": message}

        earlier_counts = [count for date, count in counts_by_date.items() if date < download_date]
        if not earlier_counts:
            message = f"INFO: {self.BROKER_NAME}: {current_rows} row(s) for {download_date}, no earlier day to compare against yet."
            print(message)
            return {"broker": self.BROKER_NAME, "alarm": False, "message": message, "current_rows": current_rows}

        average_rows = sum(earlier_counts) / len(earlier_counts)
        lower_limit = average_rows * (1 - threshold)
        upper_limit = average_rows * (1 + threshold)
        is_alarm = current_rows < lower_limit or current_rows > upper_limit
        deviation_percent = (current_rows - average_rows) / average_rows * 100

        message = (
            f"{'ALARM' if is_alarm else 'OK'}: {self.BROKER_NAME}: {current_rows} row(s) for {download_date}, "
            f"average {average_rows:.0f} over {len(earlier_counts)} earlier day(s), "
            f"deviation {deviation_percent:.2f}%, allowed range [{lower_limit:.0f}, {upper_limit:.0f}]."
        )
        print(message)
        return {
            "broker": self.BROKER_NAME,
            "alarm": is_alarm,
            "message": message,
            "current_rows": current_rows,
            "average_rows": average_rows,
            "earlier_days": len(earlier_counts),
            "deviation_percent": deviation_percent,
        }
