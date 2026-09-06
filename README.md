# tradingmachine

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

   Every setting is a `TRADINGMACHINE_`-prefixed variable. The host and port values are the host-side view, meaning `localhost` plus the published port, because the code runs on the host while the databases run as containers. The same variables are read by `docker-compose.yml` to decide which host port to publish each service on. Set any local password you like for Redis, MongoDB and Postgres; they are not shared with anything outside this machine. ChromaDB takes no credentials.

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

Four containers run on a single bridge network, `tradingmachine_network`.

| Service | Image | Host port | Container port |
|---|---|---|---|
| Redis | `redis:trixie` | 1001 | 6379 |
| MongoDB | `mongo:8.0.4` | 1002 | 27017 |
| TimescaleDB | `timescale/timescaledb:latest-pg18` | 1003 | 5432 |
| ChromaDB | `chromadb/chroma:1.5.9` | 1004 | 8000 |

Inside the network the services resolve each other by service name on the container port, so `timescaledb:5432` rather than `localhost:1003`. The host-side process does not join the network; it connects through the published ports instead.

Every port is published on `127.0.0.1` only, so the stores are not reachable from elsewhere on the network. This matters most for ChromaDB, which has had no server-side authentication since version 1.0.0 and is protected by that binding alone.

TimescaleDB serves both the relational and the timeseries workload, because TimescaleDB is a Postgres extension rather than a separate engine. Hypertables and ordinary tables live in the same database, and a hypertable is created with ordinary application-side DDL such as `SELECT create_hypertable('ohlcv', 'ts')`.

These containers belong to `tradingmachine` alone. 

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
  instruments/                   downloading the brokers' daily masters, and the daily job
  mapping/                       one cross-broker instrument identity
    rules/                       per-broker classification rules
  sql/ddl/                       table definitions, one file per table
research/                        research notebooks and backtests
utilities/                       environment-derived configuration
.claude/notes/                   commentary, one note per source file
```

The model directories are empty scaffolding at this point.

## Broker logins

Every broker issues an access token that expires at the end of the trading day. `utilities/broker_login.py` logs in to all ten and writes each token to the MongoDB `last_login` collection, one document per broker.

Credentials come from the MongoDB `settings` collection, also one document per broker, keyed on `broker_name`. Each broker wants a different set: an API key and secret, a username and password, an MPIN or a login PIN, a TOTP secret, a UCC code. Seven brokers log in over their API; Zerodha, Shoonya and Stoxkart have no login endpoint and are driven through headless Chrome.

```
python3 -m utilities.broker_login                              all ten brokers
python3 -m utilities.broker_login --brokers zerodha            just one
python3 -m utilities.broker_login --brokers dhan groww kotak   several
python3 -m utilities.broker_login --force                      log in again even if today's token exists
```

A broker whose stored token was issued today is skipped unless `--force` is given, because IND Money revokes the previous token when it issues a new one. One broker failing is reported and does not stop the others, and the exit status is 1 if any failed.

### Running it daily

`utilities/run_daily_broker_login.sh` activates the virtual environment and appends its output to a monthly log under `logs/`. Add this crontab line to run it on weekday mornings:

```
0 7 * * 1-5 /home/pramod/Projects/tradingmachine/utilities/run_daily_broker_login.sh
```

It runs at 07:00 so the day's tokens are in place before the instrument download at 07:30.

## Instrument masters

Ten brokers each publish a daily list of the instruments they will trade. `data/instruments/` downloads all ten and stores them raw in TimescaleDB, one table per broker under the `instruments` schema, one snapshot per day.

Nine of the ten are public files needing no authentication. IND Money is the exception: it wants an `Authorization` header carrying an access token that lasts twenty-four hours. That token comes from the daily broker login, which stores it in MongoDB's `last_login` collection, so run the login before the download. Without a token issued today that broker fails and the other nine still run; `--indmoney-access-token` overrides the stored one.

### Creating the tables

```
python3 -m data.create_tables
```

This applies every file under `data/sql/ddl` in filename order. Each statement is safe to run again, so the same command picks up a later change to a table.

### Downloading

```
python3 -m data.instruments.download_and_map                     download all ten, then map them
python3 -m data.instruments.download_and_map --broker zerodha    just one broker, both stages
python3 -m data.instruments.download_and_map --date 2026-09-04   override the recorded date
python3 -m data.instruments.download_and_map --bootstrap         replace a date already stored
python3 -m data.instruments.download_and_map --skip-mapping      download without mapping
```

One broker failing is reported and does not stop the others. Re-running for a date already stored is a no-op, so the daily job is safe to run twice. With `--bootstrap` that date's rows are deleted and replaced rather than appended to, so a re-ingest never doubles a day's snapshot.

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
| shoonya | 7 ZIPs | 15 | 162,247 |
| fyers | 7 CSVs | 21 | 158,943 |
| flattrade | 8 CSVs | 9 | 148,982 |
| groww | 1 CSV | 21 | 134,335 |
| zerodha | 1 CSV | 12 | 108,812 |
| indmoney | 3 CSVs | 23 | 102,949 |

### Running it daily

`data/instruments/run_daily_download_and_map.sh` activates the virtual environment, runs both stages and appends the output to a monthly log under `logs/`. Add this crontab line to run it on weekday mornings:

```
30 7 * * 1-5 /home/pramod/Projects/tradingmachine/data/instruments/run_daily_download_and_map.sh
```

It must run on the day whose files it wants, because Kotak's URL is stamped with the current date.


## Instrument mapping

The raw tables answer "what does this broker list". They cannot answer "is Zerodha's `19037442` the same contract as Shoonya's `74365`", because nothing joins them. `data/mapping/` adds that: one identity per real-world instrument, and one row per instrument per broker per day.

### The identity

An instrument's identity is its exchange, segment, shape and identity fields together — a security is its symbol, a future its underlying and expiry, an option those plus strike and option type. Each broker's adapter hashes that tuple into a UUID independently, so the same instrument seen through any broker produces the same identifier and the writes converge on one row. There is no matching step, no scoring and no registry: two brokers agree because they compute the same number, or they do not agree at all.

ISINs, tokens and tickers are used to work out *which* segment a row belongs to. None of them is the identity. Tickers do not reconcile across brokers, and four of the ten brokers publish no ISIN at all.

### Segments

Every row is classified into one canonical segment, named `{exchange}_{segment}` — `nse_equities`, `bse_equity_options`, `mcx_commodity_futures`. The vocabulary in `data/mapping/segments.py` is ordered by asset class (fixed income, equities, currencies, commodities) and within each by instrument kind (simple, futures, options, indices, index futures, index options), followed by mutual funds, exchange traded funds, investment trusts and the uncategorised buckets. Each broker's rules file must list its segments in that order, which is checked when the adapter loads.

A row no rule matches is not dropped. It goes to that exchange's `*_uncategorised` bucket, or to the plain `uncategorised` one when even the exchange cannot be determined. That keeps coverage measurable: raw rows must equal classified plus uncategorised, exactly.

### Running it

```
python3 -m data.instruments.download_and_map                                    download, then map
python3 -m data.instruments.download_and_map --mapping-only                    map today without downloading
python3 -m data.instruments.download_and_map --mapping-only --date 2026-09-04  map one stored date
python3 -m data.instruments.download_and_map --backfill                        map every stored date, oldest first
```

Downloading and mapping are one command because they are one job, but either stage can be run alone, and that matters: a download can only ever fetch today's file, since the brokers publish no history, while the mapping can be re-run over any stored date. A mapping fix is therefore applied by re-running the mapping, never by downloading again.

The broker order within the mapping is fixed, not alphabetical: several adapters resolve index names against the index rows already written for the same date, so the brokers publishing a clean index vocabulary run first. The mapping also runs after *every* download rather than after each one, because the cross-broker classification aids pool the whole day's files — a broker with no ISIN column borrows bond identities from brokers that have one.

### Asking it questions

```python
from data.mapping.resolution import resolve_broker_tokens, resolve_identity, resolve_raw_row

resolve_broker_tokens(engine, "nse", "nse_equities", "security", {"symbol": "RELIANCE"}, as_of_date)
resolve_identity(engine, "zerodha", ["738561"], as_of_date)
resolve_raw_row(engine, "fyers", "101126092974365", as_of_date)
```

The first two are the two directions an order or a position needs. The third exists because a broker's own endpoint sometimes wants an identifier the mapped tables have no column for: Fyers stores a description rather than a tradeable ticker, and its real symbol lives in the raw row. Since the stored token is each broker's join key into its own table, that row is always one lookup away.

Every lookup takes an as-of date and uses the latest mapping on or before it, so a question about a past date gets the answer that was true then.

### Verifying it

```
python3 -m data.mapping.verify_mapping --date 2026-09-04
```

Seven checks, ordered so that a failure in one explains a failure in the next: coverage per broker, identity convergence across brokers, duplicate tokens, index name convergence, resolution round-trips, backfill sanity and the uncategorised profile. It only reports; nothing raises.


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
docker compose exec timescaledb psql -U tradingmachine -d tradingmachine -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';"
```
