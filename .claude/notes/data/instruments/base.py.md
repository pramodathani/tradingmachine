# data/instruments/base.py

`BrokerInstruments` holds the machinery every broker's ingestion shares. A broker module supplies only three class attributes and a `download()` method; everything from cleaning to the database write happens here.

## What this class deliberately does not do

The instrument masters land raw. There is no classification into segments, no cross-broker instrument identity, no unified symbology, and no derived columns. Those belong to a later stage that models instruments properly, working from a faithful landing copy. In particular there is no `create_views` and no `reconcile` step.

## Everything is read and stored as text

Every broker module reads its files with `dtype=str`, and every broker column in the DDL is `TEXT`. The reason is that ingestion must not lose data.

Letting pandas infer types re-introduces a whole class of problem. The same value arrives as `2` one day and `2.0` the next, depending on whether some other row in the same chunk happened to be null. An unexpected value in a column inferred as numeric fails the whole day's load. Empty strings become indistinguishable from nulls.

Reading as text removes all of it at the source. Kotak genuinely publishes `6.16e+06` as a strike price and Fyers genuinely publishes `-1.0`; both are stored exactly as published, and interpreting them is the later stage's job.

## The cleaning steps, in order

`normalize_columns` rewrites headers into a stable lowercase SQL identifier. Several brokers bake whitespace and punctuation into the header itself rather than it being a parsing artifact: Kotak's own files ship `dTickSize ` and `dPriceNum   ` with trailing spaces, and `dStrikePrice;` with a literal semicolon. Any run of non-alphanumeric characters becomes a single underscore, which also flattens Wisdom Capital's `PriceBand.High` into `priceband_high` rather than leaving a dot that would need quoting in every query.

`strip_whitespace` trims text values. Brokers pad fields intermittently, so a value can arrive padded one day and bare the next, which would break any exact match downstream.

`drop_unnamed_columns` removes the placeholder columns pandas creates when a source file ends every line with a trailing delimiter. Dhan's scrip master and all seven of Shoonya's files do this. A column is only dropped when it is empty on every row; one carrying real values is kept and reported, so the step can never discard data silently.

`drop_garbage_rows` removes exchange test scrips such as `NSETEST`, which are never real tradeable securities.

`dedupe` drops rows repeating the broker's own natural key, sorting first when a sort column is declared so that the surviving row is predictable rather than whichever the file happened to list first.

## The unknown-column guard

`ingest` compares the downloaded frame's columns against the table's actual columns and raises if the file carries one the table does not have. The alternative, quietly reindexing the frame to the table, would drop a newly added broker column without anyone noticing, which is exactly the data loss this design is meant to prevent. When a broker adds a column, the fix is to add it to that broker's DDL file and re-run `data/create_tables.py`.

## Re-running is safe

`ingest` checks `has_data_for` first and skips a date already stored, so the daily cron job can run twice without doubling the snapshot. `--bootstrap` overrides that when a day genuinely needs re-ingesting.

## The row count deviation check

Ported from the equivalent check in `unified_broker_interface`. It compares a day's row count against the average of every earlier day and prints `OK` or `ALARM`. It never raises, because a deviation means a file worth investigating rather than a failure worth aborting on. On the first day it reports `INFO` instead, having no baseline to compare against.
