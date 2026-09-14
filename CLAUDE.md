# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state of the repository

The repository contains no source code yet. It is a git repository on the `main` branch, tracking `origin/main`. It holds `requirements.txt`, a stub `README.md`, a `pyproject.toml` that sets only the project name and version (currently `0.1.0`), a `docker-compose.yml` for the local databases, and a Python 3.14 virtual environment in `.venv/` with the required packages installed. There is no `ruff.toml` or test suite. Update this file with the real architecture once code exists.

## Environment and commands

Use the interpreter and tools inside `.venv/` directly rather than any system-wide installation.

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/ruff check .
.venv/bin/ruff format .
```

`pytest` is not in `requirements.txt` and is not installed, so it must be added before tests can be run.

`TA-Lib` is a Python wrapper around a native C library. It imports correctly in the current `.venv`, but recreating the environment on another machine requires the TA-Lib C library to be installed first.

## Local services

Redis, MongoDB and TimescaleDB run in Docker containers defined by `docker-compose.yml`. Compose reads the passwords and ports from `.env`, which is gitignored and holds the `TRADINGMACHINE_REDIS_*`, `TRADINGMACHINE_MONGODB_*` and `TRADINGMACHINE_TIMESCALEDB_*` variables used by both the containers and the Python clients.

```bash
docker compose up -d
docker compose ps
docker compose down
```

| Service | Host port | Notes |
|---|---|---|
| Redis | 2002 | Password belongs to the `default` user |
| MongoDB | 2003 | Root user, so clients connect with `authSource=admin` |
| TimescaleDB | 2004 | PostgreSQL 18 with the `timescaledb` extension |

`docker compose down -v` also deletes the `tradingmachine_*_volume` volumes and all data in them. The sibling project `unified_broker_interface` runs its own containers on ports 1002 to 1005 on the same machine. The reasoning behind the compose file is in `.claude/notes/docker-compose.yml.md`.

## Intended scope, inferred from dependencies

The pinned dependencies suggest what the project is for, but none of this is implemented yet:

| Area | Packages |
|---|---|
| Market data | `yfinance`, `requests`, `beautifulsoup4`, `selenium`, `websocket-client`, `websockets` |
| Broker login | `pyotp` (time-based one-time passwords) |
| Analysis and backtesting | `pandas`, `numpy`, `TA-Lib`, `backtesting`, `opstrat` |
| Storage | `redis`, `pymongo`, `psycopg2-binary`, `SQLAlchemy`, `peewee` |
| Interfaces | `streamlit`, `Flask`, `textual`, `uvicorn`, `gunicorn` |
