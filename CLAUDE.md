# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state of the repository

The repository contains no source code yet. It holds `requirements.txt`, a stub `README.md`, a `pyproject.toml` that sets only the project name and version (currently `0.1.0`), and a Python 3.14 virtual environment in `.venv/` with the required packages installed. It is not a git repository, and there is no `ruff.toml` or test suite. Update this file with the real architecture once code exists.

## Environment and commands

Use the interpreter and tools inside `.venv/` directly rather than any system-wide installation.

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/ruff check .
.venv/bin/ruff format .
```

`pytest` is not in `requirements.txt` and is not installed, so it must be added before tests can be run.

`TA-Lib` is a Python wrapper around a native C library. It imports correctly in the current `.venv`, but recreating the environment on another machine requires the TA-Lib C library to be installed first.

## Intended scope, inferred from dependencies

The pinned dependencies suggest what the project is for, but none of this is implemented yet:

| Area | Packages |
|---|---|
| Market data | `yfinance`, `requests`, `beautifulsoup4`, `selenium`, `websocket-client`, `websockets` |
| Broker login | `pyotp` (time-based one-time passwords) |
| Analysis and backtesting | `pandas`, `numpy`, `TA-Lib`, `backtesting`, `opstrat` |
| Storage | `redis`, `pymongo`, `psycopg2-binary`, `SQLAlchemy`, `peewee` |
| Interfaces | `streamlit`, `Flask`, `textual`, `uvicorn`, `gunicorn` |
