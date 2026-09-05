# utilities/logging.py

One function, `configure_logging(job_name)`, returning a configured standard library logger that writes to both standard error and a monthly file under `logs/`.

## Why this exists when the rest of the project uses print

Every job in the project before this one was a single process producing a linear transcript. `data.instruments.download_and_map` prints what it downloaded and what it mapped, in order, and a cron wrapper redirects that into a monthly file. For that shape of work `print` is entirely adequate and the absence of a logging setup was a deliberate simplification rather than an oversight.

The market data stream is a different shape. It runs one supervisor and twenty or more shard processes simultaneously, for fourteen hours, restarting shards as they fail. A line of output from that system is only useful if it says when it was written, how severe it is, and which of the twenty-odd processes wrote it, and none of those come for free from `print`. Levels matter too: a supervisor that logs a routine reconnection and an unrecoverable authentication failure the same way is not worth reading.

## Why it is one function and not a framework

The temptation with logging is to build a configuration layer, a set of named loggers, handlers per subsystem and a way to change levels at run time. None of that is needed here. There is one process type that needs logging, one destination pair, and one format, so the module is one function and a handful of constants, and it is small enough to read in full before using it.

Existing modules deliberately keep their `print` calls. Converting twenty working files to loggers would be churn with no benefit, and the two conventions coexist without any difficulty because they write to the same place in the end.

## Details worth knowing

The function is idempotent. It returns early if the logger already has handlers, so a module that configures logging at import time and again inside `main` does not end up emitting every line twice. This is a real hazard rather than a theoretical one, because the shard processes are started by a supervisor that has already configured its own logging.

The file name carries the year and month, computed once when the function is called. A process that runs across a month boundary therefore keeps writing to the file it opened, which matches how the existing cron wrappers behave, since they compute the month when the job starts too.

`propagate` is set to `False` so that records do not also reach the root logger. Without it, any library in the process that calls `logging.basicConfig` would cause every line to appear twice.

The rotation limit of one hundred megabytes across five files is sized for a shard logging a summary line every ten seconds plus reconnections and errors, which is a few megabytes a month. It exists to bound the damage from a fault that starts logging on every tick, not because normal operation comes anywhere near it.
