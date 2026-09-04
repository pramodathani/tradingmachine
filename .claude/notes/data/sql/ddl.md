# data/sql/ddl/

One file per table, plus `000_instruments_schema.sql` which creates the `instruments` schema. The numeric prefixes order the run in `data/create_tables.py`; they carry no other meaning.

## Every broker column is TEXT

Only `download_date` is typed, as `DATE NOT NULL`. The reasoning is in `.claude/notes/data/instruments/base.py.md` under "Everything is read and stored as text": the requirement is that ingestion never loses data, and a landing table that cannot fail on a type surprise is how that is met. Typing and interpretation belong to the later stage that models instruments.

Column names are quoted in the DDL so they match exactly what `BrokerInstruments.normalize_columns` produces, without depending on Postgres folding case the same way.

## These files were generated from the real files

The column lists were taken by downloading each broker's actual master on 2026-09-04 and running it through the cleaning steps, rather than transcribed from documentation. That is why Kotak has 80 columns rather than the 79 its FO files carry: its two `transformed-v1` cash files add `surveillanceMessage`, and stacking the seven files produces the union.

Eleven of Kotak's columns arrive empty on every row. That was checked against Kotak's own file rather than assumed: `pSubGroup`, `pCombinedSymbol`, `pAmcCode`, `pNav` and the rest are genuinely empty at source, so nothing was lost in ingestion.

## Hypertables

Each table is a TimescaleDB hypertable partitioned on `download_date`, one chunk per month. Across all nine brokers a day's snapshot is roughly 1.8 million rows, so a monthly chunk holds a few tens of millions, which is a reasonable size for TimescaleDB.

The modern `by_range` form of `create_hypertable` is used rather than the older positional `time_column_name` signature. Both exist in TimescaleDB 2.29.1, but the older one is deprecated.

## IND Money has no file yet

`data/sql/ddl` holds nine broker tables, not ten. IND Money's master sits behind an access token, so its columns could not be observed and its DDL could not be written. Once a token is available, download the file, inspect the cleaned column list, and add `100_instruments_indmoney.sql` the same way the others were made.
