# data/instruments/download.py

The command line entry point. A dictionary maps each broker name to its class, and the run loop walks it.

## One broker failing does not stop the others

Each broker runs inside its own `try`, and a failure is recorded and printed rather than raised. A single broker's file being late, malformed, or behind an expired token should not cost the day's other nine snapshots. The summary at the end names every broker that failed, and the exit is still normal, so the cron job's log is the place those failures surface.

## Why the date argument exists but rarely helps

`--date` records a different `download_date` against the rows. It does not fetch a different day's file, because nine of the ten brokers publish only their current master and keep no archive. Kotak's URL does carry a date, but it serves only today's, so a genuine backfill is not possible from any of these sources. The argument is there for correcting the recorded date, for instance when a run straddles midnight.

## IND Money is expected to fail without a token

IND Money is the only broker needing credentials, and its access token expires every twenty-four hours. A run with no token configured reports a clear `ValueError` naming the environment variable and continues with the other nine.
