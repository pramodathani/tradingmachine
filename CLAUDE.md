# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state of the repository

The repository is a git repository on the `main` branch, tracking `origin/main`. It holds `requirements.txt`, a stub `README.md`, a `pyproject.toml` that sets only the project name and version (currently `0.1.0`), a `docker-compose.yml` for the local databases, and a Python 3.14 virtual environment in `.venv/` with the required packages installed. There is no `ruff.toml` or test suite.

The source code so far is the client for the sibling project's REST API, the configuration it reads, and the instrument classes built on it:

```
utilities/configuration.py   ubi_configuration and mongodb_configuration, read from .env
ubi_client/client.py         UnifiedBrokerInterface: connect, disconnect, status, get, post, put, patch, delete
ubi_client/exceptions.py     one error class per HTTP status code UBI returns
assets/instruments.py        Instrument, TradeableInstrument, NonTradeableInstrument
assets/equities.py           the six equity-family classes, one per UBI equity segment
assets/fixed_income.py       the six fixed income classes, one per UBI fixed income segment
assets/exceptions.py         InstrumentError and its seventeen subclasses
assets/analysis/             thirteen classes of candle analysis that Instrument inherits
```

`Instrument` looks an instrument up once through `/api/instruments/details`, then fetches candles (`prices`) and live values (`quote`, `last_price`, `ohlc`) from UBI on every call. It inherits about 190 analysis methods from `assets/analysis/`: TA-Lib indicators, candlestick patterns, statistics, crossovers and a backtest. `TradeableInstrument` adds order-book values and refuses indices, and `NonTradeableInstrument` accepts only indices. There is deliberately no caching and no date-range batching around UBI calls, because UBI is local and caches in its own Redis.

`TradeableInstrument` also trades. `place_order`, `modify_order`, `cancel_order` and `cancel_open_orders` write to UBI's order routes, and `orders`, `open_orders`, `completed_orders`, `rejected_orders`, `cancelled_orders`, `trades` and the `net_positions` and `day_positions` properties read this instrument's own rows out of the account-wide documents UBI serves. The order vocabulary is passed as plain strings, such as `"buy"` and `"limit"`, because UBI validates it; prices and quantities are sent exactly as given, with no tick rounding or lot checking; and the reading members return a pandas DataFrame, or None when no row matches. Holdings and funds are not part of this, and holdings stay on `Equity`.

On top of `place_order` sit twenty-eight wrappers whose names say where the price comes from, such as `buy_at_market_price`, `sell_at_limit_price`, `buy_at_best_bid_price` and `sell_at_third_best_offer_price`. Each takes `quantity`, `product`, `validity`, `after_market` and `tag`, with `product` required so that delivery or intraday is always stated, and each raises `assets.exceptions.OrderError` when the order book has no price to use.

`add_to_position`, `reduce_position`, `liquidate_position` and `liquidate_all_positions` act on what `net_positions` reports, working out the direction from the position itself, so a long position is reduced by selling and a short one by buying. They raise `assets.exceptions.PositionError` when there is no position to act on, when several are held and none was named, or when a reduction is larger than the position. Their one trap is that UBI names a position's product `delivery`, `intraday` or `carry` while orders are sent as `cnc`, `mis` or `nrml`, and that a position under `margin_trading`, `cover` or `bracket` cannot be closed through UBI at all, so it is invisible to every one of them except `liquidate_all_positions`, which reports it as ignored.

The `positions_value` and `positions_pnl` properties add up what the instrument's positions are worth and what they have made. UBI prices a holding but not a position, so the value is the signed quantity times the last price, added across products, and it is None when any position has no last price rather than a total quietly missing a part. Both count every position, including the three kinds UBI cannot place an order for, because they are still real money.

`assets/equities.py` puts a named class on each of UBI's six equity segments, so the kind of contract is the class rather than a segment string, and each constructor takes only the fields that identify one of its own contracts: `Equity` and `EquityIndex` by exchange and symbol, `EquityFutures` and `EquityIndexFutures` by exchange, underlying symbol and expiry date, and `EquityOption` and `EquityIndexOption` by those three plus a strike price and an option type. `EquityIndex` is built on `NonTradeableInstrument` and the other five on `TradeableInstrument`. A derivative deliberately does not hold an object for its underlying, because UBI links the two only by matching symbol strings. `Equity` alone can be held for the long term, so it alone carries the holdings members: the `holdings`, `holdings_value` and `holdings_pnl` properties, and `add_to_holdings`, `reduce_holdings` and `liquidate_holdings`, which always send `cnc` orders because that is the only product that buys into or sells out of a demat holding. Selling works on the shares free to sell, which is the holding minus anything pledged as collateral, and `assets.exceptions.HoldingError` covers a share that is not held, a sale larger than the free shares, and a holding that is entirely pledged. Note that a holding's `pnl` reports `day_change`, `day_change_percentage` and `unrealized`, while a position's reports `realized`, `unrealized` and `total`. The equivalent classes for commodities, currencies and funds are not ported yet.

`assets/fixed_income.py` is the same six classes for UBI's fixed income segments, built the same way and copied from the equity module rather than sharing a base with it: `FixedIncome`, `FixedIncomeFutures`, `FixedIncomeOption`, `FixedIncomeIndex`, `FixedIncomeIndexFutures` and `FixedIncomeIndexOption`, with `FixedIncome` alone carrying the holdings members. Three things about it differ from equities and will surprise a caller who assumes otherwise. A bond is named by its ISIN, such as `IN000126C010`, rather than by a ticker, the exception being about eighty interest rate underlyings on the nse named by a rate code such as `633GS2035`, which are what the futures and options are written on; sovereign gold bonds are in this family too. No broker that serves quotes carries a cash bond or a rate index, so `quote`, `last_price` and the order-book values raise `ServiceUnavailableError` for `FixedIncome` and `FixedIncomeIndex` while the three derivative classes are quoted normally. And UBI stores no candles for any fixed income segment, so `prices` returns None throughout and the analysis methods have nothing to work on. `fixed_income_index_options` is a segment no broker fills, so `FixedIncomeIndexOption` resolves nothing today and exists for symmetry. UBI's own order routing for bond derivatives also looks wrong, sending them to the equity derivative venue rather than the currency one; the reasoning is in `.claude/notes/assets/fixed_income.py.md`.

Instruments can also be found rather than only named. `Equity.search` and `EquityIndex.search` look a symbol up by part of its name, and the four derivative classes offer `expiries`, `contracts`, `strikes` and `chain`, each supplying its own segment. These read `/api/instruments/master` rather than `/api/instruments/search`, because the search route sorts by expiry ascending, caps at 200 rows and takes no offset, so every live contract sits behind thousands of expired ones. They return a pandas DataFrame of identities rather than instrument objects, since a 214-contract option chain would otherwise mean 214 lookups, and expired contracts are left out unless `include_expired=True`.

Imports use full package paths (`from ubi_client import client`), so scripts run from the project root with the root on `PYTHONPATH`. Reasoning behind each file is in `.claude/notes/`, mirroring the source tree.

## The Unified Broker Interface (UBI)

The sibling project `../unified_broker_interface` exposes REST APIs for trading on Indian markets, and this project trades through it rather than talking to brokers directly. It is served on `http://127.0.0.1:8080`, set in `.env` as `TRADINGMACHINE_UBI_BASE_URL`.

`UnifiedBrokerInterface` reads UBI's api key and secret from this project's MongoDB, from the `settings` document `{"broker_name": "unified_broker_interface", "api_key": ..., "api_secret": ...}`, which must match the same document in UBI's own MongoDB. It was seeded by hand and is not created by any code.

UBI holds one access token for the whole application, and it expires after a day by default. Every `connect` replaces it, which logs out any other client using UBI, including UBI's REST API test page. The client reconnects and retries once when a request gets HTTP 401. See `.claude/notes/ubi_client/client.py.md`.

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

The pinned dependencies suggest what the project is for. Apart from the UBI client and the instrument classes, none of this is implemented yet:

| Area | Packages |
|---|---|
| Market data | UBI's REST API through `assets.instruments`, which is implemented; `yfinance`, `beautifulsoup4`, `selenium`, `websocket-client`, `websockets` |
| Broker access | `requests` through `ubi_client`, which is implemented; `pyotp` (time-based one-time passwords) |
| Analysis and backtesting | `pandas`, `numpy`, `TA-Lib` and `backtesting` through `assets.analysis`, which is implemented; `opstrat` |
| Storage | `redis`, `pymongo`, `psycopg2-binary`, `SQLAlchemy`, `peewee` |
| Interfaces | `streamlit`, `Flask`, `textual`, `uvicorn`, `gunicorn` |
