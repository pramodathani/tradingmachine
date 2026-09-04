# data/instruments/download_and_map.py

The command line entry point for the whole daily instrument job. Two dictionaries map each broker name to its downloader class and to its mapping adapter class, and the run walks the first, then the second.

## Why the two stages are one command

They are one job: the day's masters are downloaded and then given a cross-broker identity, and neither half is useful alone on a given morning. Keeping them in one module also keeps the broker list in one place, so a broker cannot be added to the download and forgotten in the mapping.

They are still separately runnable, and that is not symmetry for its own sake. The two stages differ in how repeatable they are: a download can only ever fetch today's file, because the brokers publish no history, while the mapping can be re-run over any date already stored. So a mapping fix is applied with `--mapping-only` or `--backfill` over stored dates, and never by downloading again — there is nothing to download again. Without those flags a corrected adapter could not be applied to any date but today, which would make the stored history permanently wrong.

`--skip-mapping` is the other direction, for when only the raw capture matters.

## The mapping's broker order is fixed

`PROCESSING_ORDER` is not alphabetical and not arbitrary. Several adapters resolve their index names by normalizing against the index rows already written to `instruments.master` for the same date, so the brokers that publish a clean index vocabulary — Dhan first, then Kotak, Groww and Stoxkart — must run before the brokers that need normalizing against it. Zerodha runs last because it needs the most from the others: six cross-broker allowlists, the shared security identifier map, and the index lookup.

Change the order and index names stop converging, quietly: nothing errors, the same real index simply ends up under two identities from two brokers.

## Why the mapping waits for every download

The cross-broker classification aids pool the whole day's raw files. A broker with no ISIN column gets its bond identities and its fund allowlists from brokers that have one, so the mapping must see the complete day. That is why the mapping stage runs after the whole download loop rather than after each broker.

## Backfill order

`--backfill` maps every stored snapshot date, oldest first. The order matters for `first_seen_date`: a master row's first seen date is set when the instrument is first written and left alone afterwards, so mapping the dates out of order would record a first sighting later than the true one.

## A broker with no rows is skipped, not failed

The mapping stage skips a broker with no raw rows for the date, with a printed notice, so a late or failed download degrades to being absent from that day's mapping rather than aborting it.

## One broker failing does not stop the others

Each broker runs inside its own `try`, and a failure is recorded and printed rather than raised. A single broker's file being late, malformed, or behind an expired token should not cost the day's other nine snapshots. The summary at the end names every broker that failed, and the exit is still normal, so the cron job's log is the place those failures surface.

## Why the date argument exists but rarely helps

`--date` records a different `download_date` against the rows. It does not fetch a different day's file, because nine of the ten brokers publish only their current master and keep no archive. Kotak's URL does carry a date, but it serves only today's, so a genuine backfill is not possible from any of these sources. The argument is there for correcting the recorded date, for instance when a run straddles midnight.

## IND Money is expected to fail without a token

IND Money is the only broker needing credentials, and its access token expires every twenty-four hours. A run with no token configured reports a clear `ValueError` naming the environment variable and the command line flag, then continues with the other nine.

The token reaches the ingester two ways: `BLACK_BOX_INDMONEY_ACCESS_TOKEN` in `.env`, or `--indmoney-access-token` on the command line, which wins when both are set. `download_one` constructs the IND Money ingester specially, passing the token through, while every other broker is constructed with no arguments. The command line flag exists because a shell history is easier to clear than a file: the token is short-lived and sensitive, and putting it in `.env` means it lingers there after it has expired.
