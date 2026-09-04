# data/mapping/run_mapping.py

The command line entry point, shaped deliberately like `data/instruments/download.py`: the same argument names, the same per-broker isolation, the same end-of-run summary. Someone who knows how to run the download knows how to run the mapping.

## Why the broker order is fixed

`PROCESSING_ORDER` is not alphabetical and not arbitrary. Several adapters resolve their index names by normalizing against the index rows already written to `instruments.master` for the same date, so the brokers that publish a clean index vocabulary — Dhan first, then Kotak, Groww and Stoxkart — must run before the brokers that need normalizing against it. Zerodha runs last because it needs the most from the others: six cross-broker allowlists, the shared security identifier map, and the index lookup.

Change the order and index names stop converging, quietly: nothing errors, the same real index simply ends up under two identities from two brokers.

## Why the mapping runs after every download, not after each one

The cross-broker classification aids pool the whole day's raw files. A broker with no ISIN column gets its bond identities and its fund allowlists from brokers that do, so the mapping must see the complete day. That is why one line was appended to `data/instruments/run_daily_download.sh` after the download line rather than the mapping being wired per broker.

## Skipping rather than failing

A broker with no raw rows for the date is skipped with a printed notice, so a late or failed download degrades to "absent from today's mapping" instead of aborting the run. A broker that raises is caught, reported with its traceback, and the rest continue — the same reasoning as the download.

## Backfill

`--backfill` maps every stored snapshot date, oldest first. The order matters for `first_seen_date`: the master row's first seen date is set when the instrument is first written and left alone afterwards, so mapping the dates out of order would record a first sighting later than the true one.
