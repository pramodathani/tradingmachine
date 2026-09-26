# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state of the repository

The repository is a git repository on the `main` branch, tracking `origin/main`. It is an installable Python library named `tradingmachine`, converted from a flat script layout on 2026-09-20. It holds a `pyproject.toml` with the library's metadata, dependencies and hatchling build backend, a `requirements.txt` pinning the wider development environment, a `README.md` describing the project, a `docker-compose.yml` for the local databases, an `mkdocs.yml`, a `docs/` tree and a `.github/workflows/docs.yml` for the documentation site, a `scripts/` directory for the documentation build tooling, and a Python 3.14 virtual environment in `.venv/` with the library installed editable. There is no `ruff.toml` and no `[tool.ruff]` section. A `tests/` directory holds a pytest suite that runs offline, against a fake UBI server on a local port, so it never places an order. There is no `LICENSE` file either, and `pyproject.toml` deliberately declares no licence until one is chosen.

All library code lives under `src/tradingmachine`, so the repository root is not importable and the library must be installed before it can be used. The source code so far is the client for the sibling project's REST API, the configuration it reads, the instrument classes built on it, the synthetic order classes and the account:

```
src/tradingmachine/utilities/configuration.py   Configuration, which reads the environment and .env lazily
src/tradingmachine/ubi_client/client.py         UnifiedBrokerInterface: connect, disconnect, status, get, post, put, patch, delete
src/tradingmachine/ubi_client/exceptions.py     one error class per HTTP status code UBI returns
src/tradingmachine/assets/instruments.py        Instrument, TradeableInstrument, NonTradeableInstrument
src/tradingmachine/assets/equities.py           the six equity-family classes, one per UBI equity segment
src/tradingmachine/assets/fixed_income.py       the six fixed income classes, one per UBI fixed income segment
src/tradingmachine/assets/commodities.py        the six commodity classes, one per UBI commodity segment
src/tradingmachine/assets/currencies.py         the six currency classes, one per UBI currency segment
src/tradingmachine/assets/funds.py              ExchangeTradedFund and InvestmentTrust, which trade like shares
src/tradingmachine/assets/mutual_funds.py       MutualFund, which is held rather than traded
src/tradingmachine/assets/exceptions.py         InstrumentError and its thirty-one subclasses
src/tradingmachine/assets/analysis/             thirteen classes of candle analysis that Instrument inherits
src/tradingmachine/orders/synthetic_order.py    SyntheticOrder, the shared base of the synthetic order types
src/tradingmachine/orders/order_candidate.py    OrderCandidate, one leg of a multi-instrument synthetic order
src/tradingmachine/orders/exposure_watch.py     ExposureWatch, one watched instrument of an exposure hedge
src/tradingmachine/orders/                      one module per UBI synthetic order type, forty-two in all
src/tradingmachine/accounts/account.py          Account, whose flatten is UBI's account-wide kill switch
scripts/gen_ref_pages.py                        builds the API reference at documentation build time
scripts/documentation_hooks.py                  silences one griffe warning during a strict docs build
.github/workflows/docs.yml                      builds the documentation site and publishes it on GitHub Pages
```

`scripts/` is deliberately outside the package, because those two files only run inside a MkDocs build and should not ship to anyone installing the library.

`Instrument` looks an instrument up once through `/api/instruments/details`, then fetches candles through the `prices` method and live values through the `quote`, `last_price` and `ohlc` properties, going to UBI on every read. Every member that only reports a value is a property, and only members that take an argument or write to the market are methods, which the user decided on 2026-09-22. It inherits about 190 analysis methods from `src/tradingmachine/assets/analysis/`: TA-Lib indicators, candlestick patterns, statistics, crossovers and a backtest. `TradeableInstrument` adds order-book values and refuses indices, and `NonTradeableInstrument` accepts only indices. There is deliberately no caching and no date-range batching around UBI calls, because UBI is local and caches in its own Redis.

`TradeableInstrument` also trades. `place_order`, `modify_order`, `cancel_order` and `cancel_open_orders` write to UBI's order routes, and the `orders`, `open_orders`, `completed_orders`, `rejected_orders`, `cancelled_orders`, `trades`, `net_positions` and `day_positions` properties read this instrument's own rows out of the account-wide documents UBI serves. `orders` gives every order today whatever its status, and a status without a property of its own, such as `EXPIRED`, is found by filtering its `status` column. The order vocabulary is passed as plain strings, such as `"buy"` and `"limit"`, because UBI validates it; prices and quantities are sent exactly as given, with no tick rounding or lot checking; and the reading members return a pandas DataFrame, or None when no row matches. Holdings and funds are not part of this, and holdings stay on `Equity`.

On top of `place_order` sit thirty-two wrappers whose names say where the price comes from, such as `buy_at_market_price`, `sell_at_limit_price`, `buy_at_best_bid_price`, `sell_at_third_best_offer_price` and `buy_at_marketable_price`. Each takes `quantity`, `product`, `validity`, `after_market` and `tag`, with `product` required so that delivery or intraday is always stated. Apart from the market and limit pairs, they do not read the order book themselves: each sends UBI a `price_reference` naming the level, the midpoint, the day's average, the last price or the marketable price, and UBI works the price out and rounds it to the tick when it sends the order. An empty or shallow book therefore comes back from UBI as `ServiceUnavailableError`, and there is no `OrderError` any more.

`add_to_position`, `reduce_position`, `liquidate_position` and `liquidate_all_positions` act on this instrument's positions without being told a side, so a long position is reduced by selling and a short one by buying. `add_to_position` reads the position and works the direction out itself; `reduce_position` and `liquidate_position` send a `quantity_reference`, and UBI reads the position, chooses the side and sizes the order when it sends it, capping a reduction at what is held so it closes the whole position rather than turning it round. They raise `tradingmachine.assets.exceptions.PositionError` when no product is named and there is not exactly one position, and a named product that is not held comes back from UBI as `ConflictError`. Their one trap is that UBI names a position's product `delivery`, `intraday` or `carry` while orders are sent as `cnc`, `mis` or `nrml`, and that a position under `margin_trading`, `cover` or `bracket` cannot be closed through UBI at all, so it is invisible to every one of them except `liquidate_all_positions`, which reports it as ignored.

The `positions_value` and `positions_pnl` properties add up what the instrument's positions are worth and what they have made. UBI prices a holding but not a position, so the value is the signed quantity times the last price, added across products, and it is None when any position has no last price rather than a total quietly missing a part. Both count every position, including the three kinds UBI cannot place an order for, because they are still real money.

UBI gained an order engine on 2026-09-23, and the user decided on 2026-09-26 that order types are built in UBI rather than here. So anything UBI can work out itself is sent as a description: `place_order` takes `price_reference`, `quantity_reference` and `synthetic` dicts after `dry_run`, and `quantity` may be None when a reference supplies it. UBI acts on those only in engine mode and silently ignores them in direct mode, so before the first such order `place_order` sends the same body as a dry run and raises `tradingmachine.ubi_client.exceptions.DirectPlacementError`, sending nothing, unless the answer carries the `intent_id` the engine adds; the finding is kept on the shared client as `placement_mode`. Plain orders are untouched and work in either mode.

`src/tradingmachine/orders/` holds one self-contained class for each of the forty-two synthetic order types in UBI's registry, each in its own module with UBI's abbreviations spelled out (`oto` is `one_triggers_other`, `gtt` is `good_till_triggered`, `atr_trail` is `average_true_range_trail`). Each takes an instrument, the order template's fields and its own settings, all by keyword, and `place()` sends it through `place_order`; nothing is validated locally. In the price-trigger types and the hidden stops UBI's synthetic `trigger_price` is the level that fires the order, so those classes store it as `trigger_level`. The multi-instrument types take `OrderCandidate` or `ExposureWatch` objects, and the first candidate anchors the request. UBI's count of forty-eight order types comes from the "Synthetic Order Atlas" artifact: forty are classes, `simple` and `virtual_limit` are classes that are not Atlas rows, and eight need no class and are reached through the price wrappers, `validity`, plain `sl` orders, `Account.flatten` and `LossLockoutError`. The Atlas's group G is mostly unbuilt in UBI, as the former Known issues page lists; the documentation rebuild of 2026-09-26 removed that page, and `git show b5761c0:docs/contributing/known-issues.md` still prints it.

`src/tradingmachine/accounts/account.py` holds `Account`, which shares the instruments' client through `Instrument.shared_unified_broker_interface()`. Its `flatten` sends `POST /api/orders/flatten`, which cancels every open order at every broker and then closes every position in the whole account; the caller types the `confirm` word `FLATTEN`, and armed synthetic orders survive it.

`src/tradingmachine/assets/equities.py` puts a named class on each of UBI's six equity segments, so the kind of contract is the class rather than a segment string, and each constructor takes only the fields that identify one of its own contracts: `Equity` and `EquityIndex` by exchange and symbol, `EquityFutures` and `EquityIndexFutures` by exchange, underlying symbol and expiry date, and `EquityOption` and `EquityIndexOption` by those three plus a strike price and an option type. `EquityIndex` is built on `NonTradeableInstrument` and the other five on `TradeableInstrument`. A derivative deliberately does not hold an object for its underlying, because UBI links the two only by matching symbol strings. `Equity` alone can be held for the long term, so it alone carries the holdings members: the `holdings`, `holdings_value` and `holdings_pnl` properties, and `add_to_holdings`, `reduce_holdings` and `liquidate_holdings`, which always send `cnc` orders because that is the only product that buys into or sells out of a demat holding. Selling works on the shares free to sell, which is the holding minus anything pledged as collateral, and `tradingmachine.assets.exceptions.HoldingError` covers a share that is not held, a sale larger than the free shares, and a holding that is entirely pledged. Note that a holding's `pnl` reports `day_change`, `day_change_percentage` and `unrealized`, while a position's reports `realized`, `unrealized` and `total`. The equivalent classes for commodities, currencies and funds are not ported yet.

`src/tradingmachine/assets/fixed_income.py` is the same six classes for UBI's fixed income segments, built the same way and copied from the equity module rather than sharing a base with it: `FixedIncome`, `FixedIncomeFutures`, `FixedIncomeOption`, `FixedIncomeIndex`, `FixedIncomeIndexFutures` and `FixedIncomeIndexOption`, with `FixedIncome` alone carrying the holdings members. Three things about it differ from equities and will surprise a caller who assumes otherwise. A bond is named by its ISIN, such as `IN000126C010`, rather than by a ticker, the exception being about eighty interest rate underlyings on the nse named by a rate code such as `633GS2035`, which are what the futures and options are written on; sovereign gold bonds are in this family too. No broker that serves quotes carries a cash bond or a rate index, so `quote`, `last_price` and the order-book values raise `ServiceUnavailableError` for `FixedIncome` and `FixedIncomeIndex` while the three derivative classes are quoted normally. And UBI stores no candles for any fixed income segment, so `prices` returns None throughout and the analysis methods have nothing to work on. `fixed_income_index_options` is a segment no broker fills, so `FixedIncomeIndexOption` resolves nothing today and exists for symmetry. UBI's own order routing for bond derivatives also looks wrong, sending them to the equity derivative venue rather than the currency one; the reasoning is in `.claude/notes/src/tradingmachine/assets/fixed_income.py.md`.

`src/tradingmachine/assets/commodities.py` is the same six classes for UBI's commodity segments, on `mcx`, `ncdex` and `nse`, with readable ticker symbols such as `GOLD` and `MCXBULLDEX`. It carries no holdings members at all, because UBI's `CASH_SEGMENTS` excludes commodities, so a commodity can never be reported as a holding. Three things about it differ from the earlier families. An order's quantity is counted in quotation units and must be a whole number of lots, so `quantity=1` on an MCX gold future is refused with HTTP 400 and `quantity=100` is one lot; on the `ncdex` that unit is tonnes although prices are quoted in quintals. `Commodity` and `CommodityIndex` cannot be ordered at all, because their rows are the exchange's underlying reference records rather than tradeable contracts, and they have no quote either. And the four derivative classes do have candles, which makes them the first instruments outside equities where the inherited analysis methods return anything. An order here can also be refused with HTTP 503 and a `contract_size_status` when UBI does not trust the contract's size that day, which is not the same as UBI being unavailable; the reasoning is in `.claude/notes/src/tradingmachine/assets/commodities.py.md`.

`src/tradingmachine/assets/currencies.py` is the same six classes for UBI's currency segments, on the `nse` and the `bse`, covering the seven pairs UBI carries and the bse's over-the-counter variants. It carries no holdings members either, for the same reason as commodities, and ordering works as it does there. Three of its six segments hold no rows on any exchange, so `CurrencyIndex`, `CurrencyIndexFutures` and `CurrencyIndexOption` resolve nothing today and exist for symmetry; they fail cleanly, raising their own error and returning empty from the discovery calls. Two further traps are specific to this family. The `lot_size` attribute is not the lot an order is measured against: it is the plurality of the brokers' figures, which gives NSE `USDINR` a lot of 1 while the bse reports 1000, whereas orders use UBI's own morning contract-size decision, so an order quantity must never be computed from `lot_size` here. And coverage varies by exchange, since the nse derivatives are quoted while the bse ones are not, and nothing in the family has candles; the reasoning is in `.claude/notes/src/tradingmachine/assets/currencies.py.md`.

`src/tradingmachine/assets/funds.py` is two classes rather than six, because UBI carries no futures or options on a fund or a trust and has no segment for them: `ExchangeTradedFund` on `exchange_traded_funds` and `InvestmentTrust` on `investment_trusts`, both named by exchange and symbol and listed on the `nse` and the `bse`. Both behave like shares, being quoted continuously, taking ordinary market and limit orders with quantity as a plain count of units, and being holdable, so both carry the same six holdings members `Equity` does. The one difference between them is what UBI stores: a fund's candles are adjusted and carry a `price_factor` column, while no candles are stored for a trust at all, so `prices` returns None there and the analysis methods have nothing to work on; the reasoning is in `.claude/notes/src/tradingmachine/assets/funds.py.md`.

`src/tradingmachine/assets/mutual_funds.py` holds `MutualFund` alone, on UBI's `mutual_funds` segment, which has 279 schemes on the `nse` and none elsewhere. A scheme is named by the exchange's code for it, such as `ABSLFTTIDG`, rather than by its published name. It is kept apart from `src/tradingmachine/assets/funds.py` because it does not behave like the two classes there: it is subscribed to at its net asset value rather than traded, no broker that serves quotes carries the segment, so `last_price` and the order-book values raise `ServiceUnavailableError`, and UBI stores no candles, so `prices` returns None. Holding is what it is for, and it carries the same six holdings members `Equity` does, which is a deliberate choice for consistency over the old project's holdings-read-only design. Because there is no quote, give those methods a limit price rather than letting them send a market order; the reasoning is in `.claude/notes/src/tradingmachine/assets/mutual_funds.py.md`.

With these seven modules, every asset class the old project had is ported. What remains unported is the `uncategorised` catch-all segment, which UBI does not accept orders for.

Instruments can also be found rather than only named. `Equity.search` and `EquityIndex.search` look a symbol up by part of its name, and the four derivative classes offer `expiries`, `contracts`, `strikes` and `chain`, each supplying its own segment. These read `/api/instruments/master` rather than `/api/instruments/search`, because the search route sorts by expiry ascending, caps at 200 rows and takes no offset, so every live contract sits behind thousands of expired ones. They return a pandas DataFrame of identities rather than instrument objects, since a 214-contract option chain would otherwise mean 214 lookups, and expired contracts are left out unless `include_expired=True`.

Imports use full package paths from the top-level package (`from tradingmachine.ubi_client import client`), and they work from any directory once the library is installed. Reasoning behind each file is in `.claude/notes/`, mirroring the source tree, so `src/tradingmachine/assets/equities.py` is documented by `.claude/notes/src/tradingmachine/assets/equities.py.md`.

## The Unified Broker Interface (UBI)

The sibling project `../unified_broker_interface` exposes REST APIs for trading on Indian markets, and this project trades through it rather than talking to brokers directly. It is served on `http://127.0.0.1:8080`, set in `.env` as `TRADINGMACHINE_UBI_BASE_URL`.

`UnifiedBrokerInterface` reads UBI's api key and secret from this project's MongoDB, from the `settings` document `{"broker_name": "unified_broker_interface", "api_key": ..., "api_secret": ...}`, which must match the same document in UBI's own MongoDB. It was seeded by hand and is not created by any code.

UBI holds one access token for the whole application, and it expires after a day by default. Every `connect` replaces it, which logs out any other client using UBI, including UBI's REST API test page. The client reconnects and retries once when a request gets HTTP 401. See `.claude/notes/src/tradingmachine/ubi_client/client.py.md`.

The library assumes UBI runs with `UNIFIED_BROKER_INTERFACE_API_ORDER_PLACEMENT=engine`, which the user's UBI `.env` sets. The price-reference wrappers, `reduce_position`, `liquidate_position` and every class in `tradingmachine.orders` depend on it, and `place_order` refuses to send their orders otherwise.

## Environment and commands

Use the interpreter and tools inside `.venv/` directly rather than any system-wide installation.

```bash
.venv/bin/python -m pip install -e ".[docs,development]"
.venv/bin/ruff check .
.venv/bin/ruff format .
```

`pyproject.toml` declares only the seven packages the library imports: `backtesting`, `numpy`, `pandas`, `pymongo`, `python-dotenv`, `requests` and `TA-Lib`. The `docs` extra holds the MkDocs toolchain and the `development` extra holds `ruff` and `build`. Everything else the project may eventually want, such as `streamlit`, `selenium` and `yfinance`, stays pinned in `requirements.txt` as the development environment and is not a dependency of the library.

`pytest` is in the `development` extra and its settings are under `[tool.pytest.ini_options]` in `pyproject.toml`. Run the suite with `.venv/bin/python -m pytest`. The tests send real HTTP requests to `tests/fake_ubi_server.py`, which issues its own tokens, and replace `pymongo.MongoClient` with the fakes in `tests/fakes.py`, so nothing reaches UBI, a broker or a database.

`TA-Lib` is a Python wrapper around a native C library. It imports correctly in the current `.venv`, but recreating the environment on another machine requires the TA-Lib C library to be installed first.

## Documentation

The project has a Material for MkDocs site, published at https://pramodathani.github.io/tradingmachine/. It was first added on 2026-09-20 and rebuilt from scratch on 2026-09-26, following the sibling project's rebuild of the day before, with the same deep orange palette, Mermaid diagrams, Vega-Lite charts and animated SVGs in `docs/assets/diagrams/`. Narrative pages are hand-written under `docs/` and listed in the `nav` in `mkdocs.yml`; reference pages are generated at build time by `scripts/gen_ref_pages.py`, one per module under `src/tradingmachine`, straight from the docstrings, and held in memory rather than written into the repository. `site/` is gitignored.

The site has seven tabs: Get started, Python API, Asset classes, Analysis, Architecture, Project and the generated API reference. The Python API tab is laid out like Zerodha's Kite Connect documentation, with one page per group of members, a summary table on each, and member badges from `docs/stylesheets/extra.css` that mark which members place real orders. `docs/project/writing-docs.md` holds the visual conventions a new page should follow. The old Pitfalls and Known issues pages were not carried over, at the user's choice; they remain in git history at `b5761c0`.

`.github/workflows/docs.yml` builds the site with `mkdocs build --strict` on every push and pull request, and publishes it to GitHub Pages only from `main`, so merging a pull request republishes the site and a broken link fails the pull request's check. It installs only the `docs` extra from `pyproject.toml`, because installing the library would need TA-Lib's C library; the reasoning is in `.claude/notes/.github/workflows/docs.yml.md`.

```bash
.venv/bin/mkdocs serve
.venv/bin/mkdocs build --strict
```

Two settings differ from the sibling's configuration and both matter. `inherited_members` is `false`, because with it on, all twenty-seven family classes reprinted the 190 inherited analysis methods and the site came out at 151 MB with 24 MB pages. `scripts/documentation_hooks.py` is registered under `hooks:` to filter one griffe warning provoked by this project's `Raises:\n    Nothing.` convention, which would otherwise fail every strict build; nothing else is suppressed. The reasoning is in `.claude/notes/mkdocs.yml.md`.

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

The pinned dependencies suggest what the project is for. Apart from the UBI client, the instrument classes, the synthetic order classes and the account, none of this is implemented yet:

| Area | Packages |
|---|---|
| Market data | UBI's REST API through `tradingmachine.assets.instruments`, which is implemented; `yfinance`, `beautifulsoup4`, `selenium`, `websocket-client`, `websockets` |
| Broker access | `requests` through `ubi_client`, which is implemented; `pyotp` (time-based one-time passwords) |
| Analysis and backtesting | `pandas`, `numpy`, `TA-Lib` and `backtesting` through `tradingmachine.assets.analysis`, which is implemented; `opstrat` |
| Storage | `redis`, `pymongo`, `psycopg2-binary`, `SQLAlchemy`, `peewee` |
| Interfaces | `streamlit`, `Flask`, `textual`, `uvicorn`, `gunicorn` |
