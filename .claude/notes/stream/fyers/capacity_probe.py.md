# stream/fyers/capacity_probe.py

## Why measuring matters more for Fyers than for any broker so far

Fyers documents one websocket connection at a time and five thousand subscriptions on it. The instrument universe this project tracks through Fyers is about a hundred and fifty-eight thousand. If the documented numbers were true, Fyers would cover roughly three per cent of its own universe and would barely be worth streaming from.

Every broker measured so far has enforced something different from what it documented, sometimes by more than an order of magnitude, which is why the numbers are established by trying rather than read off a page. Whether Fyers is worth a shard at all is a question this probe answers and nothing else can.

## The snapshot does double duty on this broker

Every probe in this project leans on the broker sending a snapshot when it accepts a subscription, because that makes a quietly truncated subscription visible immediately and lets the probe run outside market hours when nothing would otherwise tick.

On Fyers the snapshot means more than that. It is the only packet that names its topic, so an instrument that never appears in one is an instrument whose updates could not have been decoded even if they had arrived. Counting delivered snapshots is therefore not a proxy for coverage here, it is coverage exactly.

`SnapshotCollector` counts topic names from snapshot packets alone for that reason, and resets on a new session, because Fyers renumbers topics per connection.

## The two feeds are measured and stored separately

The quote socket and the tick-by-tick socket are different sockets with different limits which may or may not draw on the same pool of connections. `stream/capacity.py` already keys a measurement on the broker and the feed together, which exists because Dhan needed it, and this uses the same mechanism: the quote feed is stored under `market_feed` and the depth feed under `tick_by_tick_depth`.

The tick-by-tick feed is probed by trying a few sizes around its documented limit of five rather than doubling upward from it. Five is small enough that a search costs nothing, and the interesting question there is not how high it goes but whether the documented five is real. The probe also records the server's error texts, because a symbol the exchange serves no tick-by-tick data for is reported that way and produces silence otherwise.

## The date sub-selects had to go, and this is why

The obvious way to write the instrument query is to put `(SELECT max(download_date) FROM instruments.fyers)` inline in the `WHERE` clause, which is what the Zerodha, Dhan, Flattrade and Shoonya probes do.

Written that way, this query intermittently returned **zero rows**. Not an error, not a partial result: the identical query text, on a fresh connection, returned the correct hundred and fifty-eight thousand rows on some runs and nothing at all on others, roughly a third of the time. A probe that got the empty answer would have measured an empty universe and reported a limit of zero, and the run after it would have looked fine.

The cause was narrowed down by elimination, and it needs three things at once:

| Condition | Result |
|---|---|
| as written | flaps between the right count and zero |
| `SET max_parallel_workers_per_gather = 0` | stable |
| `SET timescaledb.enable_chunk_append = off` | stable |
| dates written as literals instead of sub-selects | stable |
| either hypertable's sub-select alone, without the join | stable |

So it takes a parallel plan, TimescaleDB's `ChunkAppend`, and a partitioning-column value that is only known at run time. Under those three, runtime chunk exclusion intermittently excludes every chunk. Both `instruments.fyers` and `instruments.broker_mappings` are hypertables partitioned on exactly the date being compared, and the join is what makes the plan parallel.

The fix is to look the two dates up in their own statements and pass them in as bound parameters, which makes them plan-time constants. Ten consecutive runs then return the same count. This is worth preferring on its own merits anyway, since it is easier to read than a doubly-nested sub-select, but it is here for correctness rather than for style.

## The same shape exists in the four earlier brokers' probes

`stream/zerodha/capacity_probe.py`, and the Dhan, Flattrade and Shoonya equivalents, all select their instruments with the sub-select form against `instruments.broker_mappings`, which is a hypertable partitioned on `mapping_date`, joined to `instruments.master`. That is the same shape that flaps here.

They were not changed as part of the Fyers work, because one branch and one merge request cover one feature. It is recorded here so the next person to touch them knows to look, and so a Zerodha probe that one day reports an implausible limit is not debugged from scratch.

## Failing loudly on an empty universe

`live_instruments` raises `FyersProbeError` when either table is empty or the query returns nothing, rather than returning an empty list. This is the direct lesson of the flapping query: the failure that mattered was not that the database returned nothing, it was that the probe would have carried on and reported a result. A probe that cannot see any instruments has not measured a limit of zero, it has failed to run, and those must not look the same in the log.
