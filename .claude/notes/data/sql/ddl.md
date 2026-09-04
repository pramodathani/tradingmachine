# data/sql/ddl/

One file per table, plus `000_instruments_schema.sql` which creates the `instruments` schema. The numeric prefixes order the run in `data/create_tables.py`; they carry no other meaning.

## Every broker column is TEXT

Only `download_date` is typed, as `DATE NOT NULL`. The reasoning is in `.claude/notes/data/instruments/base.py.md` under "Everything is read and stored as text": the requirement is that ingestion never loses data, and a landing table that cannot fail on a type surprise is how that is met. Typing and interpretation belong to the later stage that models instruments.

Column names are quoted in the DDL so they match exactly what `BrokerInstruments.normalize_columns` produces, without depending on Postgres folding case the same way.

`080_instruments_shoonya.sql` also carries two `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements after its `CREATE TABLE`. The `CREATE TABLE` only runs when the table does not exist yet, so a column added later would never reach an already-created table; the `ALTER` statements are idempotent either way, no-ops on a fresh database and the delivery mechanism on the existing one. The two columns, Shoonya's `source_zip_url` and `source_file_name`, were added when historical snapshots imported from `unified_broker_interface`'s database arrived carrying them.

## These files were generated from the real files

The column lists were taken by downloading each broker's actual master on 2026-09-04 and running it through the cleaning steps, rather than transcribed from documentation. That is why Kotak has 80 columns rather than the 79 its FO files carry: its two `transformed-v1` cash files add `surveillanceMessage`, and stacking the seven files produces the union.

Eleven of Kotak's columns arrive empty on every row. That was checked against Kotak's own file rather than assumed: `pSubGroup`, `pCombinedSymbol`, `pAmcCode`, `pNav` and the rest are genuinely empty at source, so nothing was lost in ingestion.

## Hypertables

Each table is a TimescaleDB hypertable partitioned on `download_date`, one chunk per month. Across all ten brokers a day's snapshot is roughly 1.9 million rows, so a monthly chunk holds a few tens of millions, which is a reasonable size for TimescaleDB.

The modern `by_range` form of `create_hypertable` is used rather than the older positional `time_column_name` signature. Both exist in TimescaleDB 2.29.1, but the older one is deprecated.

## IND Money's file was written last

`100_instruments_indmoney.sql` was added after the other nine, on 2026-09-04, because IND Money's master sits behind an access token and its columns could not be observed until one was supplied. It was generated the same way as the others: from the cleaned column list of a live download, not from documentation. One of its columns, `delivery_unit`, arrives empty on every row, checked against the raw response body — same situation as Kotak's eleven empty columns.

## The mapped tables: 110 and 120

`110_instruments_master.sql` and `120_instruments_broker_mappings.sql` are not raw landing tables. They hold the cross-broker mapping that `data/mapping/` produces from the ten raw tables, so they break the "every column is TEXT" rule deliberately: `instrument_id` is a UUID, the dates are DATE, and the sizes are NUMERIC. The raw layer's job is to never lose data, and this layer's job is to interpret it, which is exactly the "later stage that models instruments" the TEXT rule defers to.

`instruments.master` holds one row per real-world instrument, keyed by a deterministic `instrument_id` that every broker's adapter computes independently as a UUID5 over the canonical natural key. The same instrument from any broker therefore converges on the same row with no matching step. It is a plain table, not a hypertable, because there is one row per instrument, not one per date; the time dimension lives in `first_seen_date` and `last_seen_date`, updated on every mapping run. The three partial unique indexes enforce the natural key per shape: `(exchange, segment, symbol)` for securities, plus underlying and expiry for futures, plus strike and option type for options.

`instruments.broker_mappings` holds one row per instrument, broker, and `mapping_date`, carrying that broker's `broker_token`, `broker_symbol`, `lot_size`, and `tick_size`. It is a hypertable chunked monthly on `mapping_date`, like the raw tables, because it is written and read the same way: a per-date snapshot, delete-then-insert per broker per date, and date-range scans in the resolution lookups. `mapping_date` rather than `download_date` is deliberate — it is the mapping run's own date, distinct from the raw snapshot's date even though the two coincide in the daily cron. The foreign key from a hypertable to the plain `master` table is supported by TimescaleDB, and the partitioning column being in the primary key is a TimescaleDB requirement.

Rows that no broker's rules can classify are not dropped: they land in `master` and `broker_mappings` under catch-all segments (`nse_uncategorised`, `bse_uncategorised`, `mcx_uncategorised`, `ncdex_uncategorised`, and unprefixed `uncategorised` when the exchange itself is unknown), which keeps coverage measurable and the raw row recoverable via broker, date, and token.
