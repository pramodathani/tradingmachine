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
research/                        research notebooks and backtests
utilities/                       environment-derived configuration
.claude/notes/                   commentary, one note per source file
```

The model directories are empty scaffolding at this point.

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
