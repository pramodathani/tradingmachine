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

## The market data tables: 200 to 230

These four files hold the streaming quote layer. They sit in their own `market_data` schema rather than in `instruments`, because they answer a different question: `instruments` describes what exists and `market_data` records what those instruments did.

### One table for every broker

`market_data.ticks` is a single hypertable that every broker's feed writes into, not one table per broker. The reason is the whole point of running several brokers at once. Zerodha lists about 109,000 instruments, which is around 44% of the roughly 247,000 live instruments the ten brokers list between them, so covering the market means several feeds running simultaneously and splitting the universe. An instrument streamed by Zerodha this month and by another broker next month has to remain one continuous series, and per-broker tables would fragment exactly the thing the multi-broker design exists to produce.

The row is therefore keyed on `instrument_id`, the same deterministic UUID that `instruments.master` uses, with `broker` and `broker_token` carried alongside as provenance. A consumer asks about an instrument; the broker that happened to deliver the quote is an attribute of the observation, not part of its identity.

`instrument_id` is nullable while `broker` and `broker_token` are not. A token that ticks without a mapping should still be recorded rather than dropped or crashed on, and provenance is always available even when the unified identity is not.

### Prices are stored as the broker sent them, with the divisor

Every price column holds the raw integer the broker put on the wire, and `price_divisor` holds the number to divide it by. Zerodha sends prices as integers in paise for most segments, in ten-millionths for NSE currency, and in ten-thousandths for both BSE currency and NSE Commodity; another broker will have its own conventions. That NSE Commodity scales differently from MCX commodity, despite both being commodity segments, is a good illustration of why the divisor is stored per row rather than derived from anything.

Storing the raw integer is exact, it is narrower than a double, and it compresses far better because integer columns delta-encode well. But "raw integer" is meaningless on its own once more than one broker writes into the table, which is why the divisor travels with the row rather than being derived at read time from the broker and segment. `220_market_data_prices.sql` then defines `market_data.ticks_priced`, a view that divides, and it contains no broker names, no segment arithmetic and no `CASE` at all — every row already carries what is needed to interpret it.

The division is wrapped in `trim_scale`. Without it Postgres returns a numeric with a scale of sixteen, so a price of 2841.55 reads back as `2841.5500000000000000` in every query result.

`market_data.divide_prices` does the same division across the depth arrays. It is a separate function only because there is no operator that divides an array by a scalar.

### Depth is arrays, and the arrays are not fixed length

The five bid and five ask levels are six arrays rather than thirty columns. Arrays keep the row readable, they compress well, and they absorb a broker that publishes twenty depth levels instead of five without any schema change. Index instruments, which carry no depth at all, simply leave them null.

### Everything from the wire is BIGINT

Broker integers are read unsigned, so a four-byte field can carry a value above 2,147,483,647. That would not fit an `INTEGER` column, and because the writer loads rows with `COPY` in batches of twenty thousand, one such value would fail the whole batch rather than one row. `BIGINT` throughout removes that failure mode. `instrument_token` is not stored as an integer at all; `broker_token` is `TEXT`, matching `instruments.broker_mappings`, so no conversion is needed to join them.

### The partitioning column is arrival_time, not exchange_timestamp

Exchange timestamps have one-second resolution and can arrive as zero or as garbage. Partitioning on a column that can be null or wrong would put rows in the wrong chunk and corrupt a chunk's time range. `arrival_time` is recorded by the shard process itself from `time.time_ns()` the moment the frame is read off the socket, so it is always present, always monotonic, and finer-grained than anything the exchange provides.

### No primary key and no secondary index

This is deliberate and it is a real trade-off. At the expected volume an index on `(instrument_id, arrival_time)` would cost tens of gigabytes a day and roughly double the cost of every insert. Ticks are an append-only observation log rather than a mutable record, and duplicates are a non-event because the raw archive is the authority on what was received. Point lookups on recent data are served by the Redis last value cache instead, and historical per-instrument access relies on the columnstore's ordering metadata. The consequence to be aware of is that a query for one instrument over the last hour will scan the uncompressed chunk.

### Chunk interval, columnstore and retention

The chunk interval is one hour, which is far shorter than the monthly chunks the instrument tables use, because the volume is orders of magnitude higher. One hour is roughly tens of gigabytes uncompressed, which keeps the two or three chunks that are still uncompressed inside the machine's memory. A daily interval would produce chunks too large to cache and a fifteen-minute interval would bloat the catalogue with tens of thousands of chunks a year. This will need revisiting when a second broker starts writing.

`segmentby` is `broker` rather than the instrument, which looks wrong at first and is not. The columnstore wants a low-cardinality segment key, and there are at most ten brokers. Segmenting by instrument would produce a long tail of tiny compressed batches, because most of the universe is deep out-of-the-money options that tick a handful of times an hour. `orderby` is `instrument_id, arrival_time DESC`, which gives long runs of the same instrument for the compressor and leaves TimescaleDB's minimum and maximum metadata on the leading column available for pruning.

Note that `add_columnstore_policy` is a procedure in TimescaleDB 2.29 and needs `CALL`, while `add_retention_policy` is still a function and needs `SELECT`. Both work inside the single transaction that `data/create_tables.py` wraps around each file.

The ninety-day retention is the value that is most likely to change. It was chosen deliberately but the estimate behind it is unverified, and ninety days of full-depth ticks may be several terabytes. The intention is to measure with `hypertable_detailed_size` and `chunk_compression_stats` after the first full session and reset `drop_after` from the measurement. Nothing is lost by shortening it, because the raw archive holds every frame and the replay tool can rebuild any window.
