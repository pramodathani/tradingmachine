# black_box

An algorithmic trading system for quantitative investing and trading in Indian markets.

The project is organised around the standard decomposition of a systematic trading process: alpha models produce signals, risk models constrain them, transaction cost models price the trades, all three models feed into portfolio construction models which turn them into target positions, and execution models place them.

The code itself runs on the host. Only its databases run in Docker.

## Prerequisites

- Python 3.14
- Docker and Docker Compose

TA-Lib needs no system library. The `TA-Lib` wheel bundles the C library.

## Setup

1. Create a virtual environment and install the dependencies.

   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy the environment template and fill in the values.

   ```
   cp .env.example .env
   ```

   Every setting is a `BLACK_BOX_`-prefixed variable. The host and port values are the host-side view, meaning `localhost` plus the published port, because the code runs on the host while the databases run as containers. The same variables are read by `docker-compose.yml` to decide which host port to publish each service on. Set any local password you like for Redis, MongoDB and Postgres; they are not shared with anything outside this machine. ChromaDB takes no credentials.

3. Start the data layer.

   ```
   docker compose up -d
   ```

   No `-p` flag is needed. The Compose project name is set by the `name:` key in `docker-compose.yml`.

4. Confirm all four containers are healthy.

   ```
   docker compose ps
   ```

## Data layer

Four containers run on a single bridge network, `black_box_network`.

| Service | Image | Host port | Container port |
|---|---|---|---|
| Redis | `redis:trixie` | 1001 | 6379 |
| MongoDB | `mongo:8.0.4` | 1002 | 27017 |
| TimescaleDB | `timescale/timescaledb:latest-pg18` | 1003 | 5432 |
| ChromaDB | `chromadb/chroma:1.5.9` | 1004 | 8000 |

Inside the network the services resolve each other by service name on the container port, so `timescaledb:5432` rather than `localhost:1003`. The host-side process does not join the network; it connects through the published ports instead.

Every port is published on `127.0.0.1` only, so the stores are not reachable from elsewhere on the network. This matters most for ChromaDB, which has had no server-side authentication since version 1.0.0 and is protected by that binding alone.

TimescaleDB serves both the relational and the timeseries workload, because TimescaleDB is a Postgres extension rather than a separate engine. Hypertables and ordinary tables live in the same database, and a hypertable is created with ordinary application-side DDL such as `SELECT create_hypertable('ohlcv', 'ts')`.

These containers belong to `black_box` alone. 

There is no dev, uat or prod tier system, and there is no `app` service or Dockerfile, because the code always runs on the host.

## Configuration

`utilities/configuration.py` reads the environment once at import time and exposes one dictionary per datastore. Code elsewhere imports from it rather than reading `os.environ` directly.

```python
from utilities.configuration import *

import redis

client = redis.Redis(
    host=redis_configuration["host"],
    port=redis_configuration["port"],
    db=redis_configuration["database"],
    username=redis_configuration["username"],
    password=redis_configuration["password"],
)
```

The four dictionaries are `redis_configuration`, `mongodb_configuration`, `postgres_configuration` and `chromadb_configuration`. Each carries `host`, `port` and `database`, plus `username` and `password` where the store has them, and the three network stores also carry a prebuilt `connection_string`.

## Project layout

```
alpha_models/                    signal generation
risk_models/                     risk constraints applied to signals
portfolio_construction_models/   signals and constraints to target positions
transaction_cost_models/         expected cost of trading into those positions
execution_models/                order placement and execution
data/                            market and reference data
  instruments/                   the brokers' daily instrument masters
  sql/ddl/                       table definitions, one file per table
research/                        research notebooks and backtests
utilities/                       environment-derived configuration
.claude/notes/                   commentary, one note per source file
```

The model directories are empty scaffolding at this point.

## Instrument masters

Ten brokers each publish a daily list of the instruments they will trade. `data/instruments/` downloads all ten and stores them raw in TimescaleDB, one table per broker under the `instruments` schema, one snapshot per day.

Nine of the ten are public files needing no authentication. IND Money is the exception: it wants an `Authorization` header carrying an access token, generated separately from `https://api.indstocks.com/generate/token` and valid for twenty-four hours. Put a current token in `BLACK_BOX_INDMONEY_ACCESS_TOKEN`; without one that broker is skipped and the other nine still run.

### Creating the tables

```
python3 -m data.create_tables
```

This applies every file under `data/sql/ddl` in filename order. Each statement is safe to run again, so the same command picks up a later change to a table.

### Downloading

```
python3 -m data.instruments.download                     all ten brokers
python3 -m data.instruments.download --broker zerodha    just one
python3 -m data.instruments.download --date 2026-09-04   override the recorded date
python3 -m data.instruments.download --bootstrap         re-ingest a date already stored
```

One broker failing is reported and does not stop the others. Re-running for a date already stored is a no-op unless `--bootstrap` is given, so the daily job is safe to run twice.

`--date` changes the date recorded against the rows; it does not fetch an older file. Nine brokers publish only their current master, and Kotak's date-stamped URL serves only today, so a genuine backfill is not possible from these sources.

### What is stored

Every broker column is `TEXT`, and only `download_date` is typed. Files are read as text so that nothing is coerced on the way in, which means the same value cannot arrive as `2` one day and `2.0` the next, and an unexpected value can never fail a day's load. Kotak publishes `6.16e+06` as a strike price and Fyers publishes `-1.0`; both are stored exactly as published. Typing and interpretation belong to a later stage.

The processing is deliberately light: column names are normalised, text values trimmed, empty artifact columns from trailing delimiters dropped, exchange test scrips removed, and rows repeating a broker's own natural key de-duplicated. There is no classification into segments and no cross-broker instrument identity.

After each broker loads, its row count is compared against the average of every earlier day and reported as `OK` or `ALARM`. A deviation is a signal to investigate, not a failure, so it never aborts the run.

### Row counts

Confirmed on 2026-09-04, the first day loaded.

| Broker | Files | Columns | Rows |
|---|---|---|---|
| stoxkart | 1 CSV | 13 | 464,383 |
| wisdom_capital | 9 POST calls | 28 | 209,385 |
| dhan | 1 CSV | 32 | 199,540 |
| kotak | 7 CSVs | 80 | 187,397 |
| shoonya | 7 ZIPs | 13 | 162,247 |
| fyers | 7 CSVs | 21 | 158,943 |
| flattrade | 8 CSVs | 9 | 148,982 |
| groww | 1 CSV | 21 | 134,335 |
| zerodha | 1 CSV | 12 | 108,812 |
| indmoney | 3 CSVs | not yet known | needs a token |

### Running it daily

`data/instruments/run_daily_download.sh` activates the virtual environment and appends its output to a monthly log under `logs/`. Add this crontab line to run it on weekday mornings:

```
30 7 * * 1-5 /home/pramod/Projects/black_box/data/instruments/run_daily_download.sh
```

It must run on the day whose files it wants, because Kotak's URL is stamped with the current date.


## Conventions

These apply across the project and are enforced by hand rather than by a formatter.

- Explanatory comments do not go in code or config files. That commentary lives in `.claude/notes/`, one Markdown file per source file, mirroring the source tree. The only exception is the section headers in `.gitignore`.
- Every function, method and class has a Google-style docstring covering the object, each parameter and its type, the return value and its type, and any exceptions raised.
- Identifiers are spelled out in full. Write `segment_configuration`, never `seg_cfg`. Well-known abbreviations such as `NSE` are kept as they are.
- Every element of a list, dictionary, tuple or set literal goes on its own line.
- A sentence never splits across lines. Sentence integrity wins over any column limit, so a formatter with a hard line cap would fight this codebase.

## Verifying the data layer

With the virtual environment active and `.env` filled in, each store can be reached from the host.

```
docker compose ps
python3 -c "from utilities.configuration import *; import redis; print(redis.Redis(host=redis_configuration['host'], port=redis_configuration['port'], password=redis_configuration['password']).ping())"
curl -s http://127.0.0.1:1004/api/v2/heartbeat
```

To confirm the TimescaleDB extension is present:

```
docker compose exec timescaledb psql -U black_box -d black_box -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';"
```
