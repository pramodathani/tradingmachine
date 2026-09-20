# Trading Machine

Trading Machine is a Python library, installed as `tradingmachine`, in which an Indian market instrument is a Python object. You name a share, a futures contract or an option once, and from that one object you get its candles, its live quote, its order book, about 190 analysis methods, the orders you have placed in it, the positions you hold in it and the units of it sitting in your demat account.

Nothing in this project talks to a broker. Every call goes to the sibling project `unified_broker_interface`, which runs on the same machine, speaks to ten Indian retail brokers and normalises what they say. This project is the layer above that, where the vocabulary stops being HTTP routes and starts being instruments.

```python
from tradingmachine.assets import equities

infosys = equities.Equity(exchange="nse", symbol="INFY")

candles = infosys.prices(days=365)
strength = infosys.relative_strength_index(window=14, days=365)
spread = infosys.bid_offer_spread()

placed = infosys.buy_at_limit_price(quantity=1, price=1450.0, product="cnc")
waiting = infosys.open_orders()
infosys.cancel_open_orders()
```

> [!CAUTION]
> This project places real orders with real money. `place_order` and its twenty-eight wrappers, the position methods and the holdings methods all reach a live broker account, and there is no paper trading mode and no simulator. `place_order(dry_run=True)` asks UBI to build the broker's request and hand it back unsent, which is the only rehearsal available.

## How it fits together

Four layers, each with one job, sitting on the UBI REST API.

```text
your script
    │
    ▼
tradingmachine.assets.equities, tradingmachine.assets.fixed_income, tradingmachine.assets.commodities,
tradingmachine.assets.currencies, tradingmachine.assets.funds, tradingmachine.assets.mutual_funds
    │   one named class per UBI segment
    ▼
tradingmachine.assets.instruments          ◄──── tradingmachine.assets.analysis
    │   identity, candles,          thirteen classes Instrument
    │   quotes, order book,         inherits: ~190 methods over
    │   orders, positions           the candles
    ▼
tradingmachine.ubi_client   ◄──── tradingmachine.utilities.configuration
    │   the session, the token,     the environment, .env and
    │   one retry, typed errors     the MongoDB connection string
    ▼
UBI REST API on 127.0.0.1:8080
    │
    ▼
ten Indian retail brokers
```

Three ideas shape everything above.

**The class is the contract type.** There is no `segment="equity_options"` string passed by hand. `EquityOption` is a class, and its constructor asks for an exchange, an underlying symbol, an expiry date, a strike price and an option type, because that is what identifies one equity option. A class that cannot be traded, such as `EquityIndex`, simply does not offer the order methods.

**Nothing is cached and nothing is validated locally.** An instrument looks itself up once, at construction, and after that every candle, quote, order and position is fetched at the moment you ask. Prices and quantities reach UBI exactly as given, with no rounding to the tick size and no checking against the lot size, because UBI and the broker behind it hold those rules and this layer would only be guessing.

**Duplication between asset classes is deliberate.** `src/tradingmachine/assets/fixed_income.py` is a copy of `src/tradingmachine/assets/equities.py` rather than a generalisation of it, and each of the five holdable classes carries its own copy of the free-to-sell arithmetic. Each family then reads as one self-contained file, and a fact true only of bonds can be written into the bond file without anyone checking what else inherits it.

## Asset class coverage

Twenty-seven classes across six modules cover every asset class UBI carries. A method can be present on a class and still have nothing to work on, so this table is worth reading before writing code against a family you have not used before.

| Family | Classes | Candles | Quotes | Orders | Holdings |
| --- | :---: | --- | --- | --- | --- |
| Equities | 6 | ✓ | ✓ | quantity in units | `Equity` only |
| Fixed income | 6 | — none, anywhere | derivatives only | quantity in units | `FixedIncome` only |
| Commodities | 6 | ✓ the four derivative classes | derivatives only | **whole lots**, derivatives only | — never |
| Currencies | 6 | — none, anywhere | nse derivatives only | **whole lots**, derivatives only | — never |
| Funds and trusts | 2 | ✓ funds only | ✓ | quantity in units | ✓ both |
| Mutual funds | 1 | — none | — none | `cnc` only, give a limit price | ✓ |

The gaps are UBI's rather than work left undone. No broker that serves quotes carries a cash bond or a rate index; UBI stores no candles for any fixed income or currency segment; and four segments — the three currency index ones and `fixed_income_index_options` — hold no rows at all on any exchange, so their classes resolve nothing today and exist so that every family has the same shape. `docs/asset-classes/index.md` carries the full table and the reason behind every gap.

> [!WARNING]
> A commodity or currency order's quantity is counted in quotation units and must be a whole number of lots: `quantity=1` on an MCX gold future is refused, `quantity=100` is one lot. The instrument's `lot_size` attribute is **not** the figure to compute that from, because it is the plurality of the brokers' own numbers, which gives NSE `USDINR` a lot of 1 while orders are measured against 1000.

## Requirements

| Requirement | Version used here | Why |
| --- | --- | --- |
| Python | 3.14 | The virtual environment in `.venv/` is built against it |
| TA-Lib C library | 0.6 or later | The `TA-Lib` package the library depends on wraps it, and `pip` cannot install the C part |
| Unified Broker Interface | running on `127.0.0.1:8080` | Every price and every order comes from it |
| MongoDB | 8.0.4 | Holds the api key and secret the UBI client authenticates with |
| Redis | `redis:trixie` | Brought up by Compose, not yet read by any module |
| PostgreSQL with TimescaleDB | 18 | The same |

Docker Compose runs the three stores, so none of them needs to be installed on the host.

## Getting started

1. **Install the TA-Lib C library first.** The Python wrapper fails to build without it, with an error about a missing symbol or header rather than a missing package, which is confusing the first time. On macOS, `brew install ta-lib`; on Debian, build the newest source release from [the TA-Lib releases page](https://github.com/ta-lib/ta-lib/releases).

2. **Create the virtual environment and install the library.** An editable install points the environment at `src/tradingmachine` where it sits, so an edit to a source file takes effect immediately, and it pulls in the seven packages the library imports. The two extras add the MkDocs toolchain and `ruff`.

   ```bash
   python3.14 -m venv .venv
   .venv/bin/python -m pip install --upgrade pip
   .venv/bin/python -m pip install -e ".[docs,development]"
   ```

   To reproduce the exact pinned environment this was developed in, install `requirements.txt` as well, then add the library on top of it with `--no-deps`.

3. **Write a `.env` file at the project root.** It needs `TRADINGMACHINE_UBI_BASE_URL` and a host, port, database, username and password for each of Redis, MongoDB and TimescaleDB. `docs/getting-started/configuration.md` lists every variable. The file is excluded by `.gitignore` and should never be committed.

4. **Bring the data stores up.** Docker Compose reads the same `.env`, so the ports and passwords come from the variables you just set. The containers use ports 2002 to 2004, chosen to stay clear of the sibling project's, which use 1002 to 1005 on the same machine.

   ```bash
   docker compose up -d
   docker compose ps
   ```

5. **Seed the UBI credentials into MongoDB.** One document in the `settings` collection, which no code in either project creates:

   ```javascript
   { "broker_name": "unified_broker_interface", "api_key": "...", "api_secret": "..." }
   ```

   The same key and secret must be present in UBI's own MongoDB, which is a separate database on a separate port. A mismatch is the first thing to check when `connect` raises an `AuthenticationError`.

Once that is done, this proves the whole chain, from the credentials through UBI to a broker that serves quotes:

```bash
.venv/bin/python -c "
from tradingmachine.assets import equities
infosys = equities.Equity(exchange='nse', symbol='INFY')
print(infosys)
print(infosys.last_price())
"
```

> [!NOTE]
> UBI holds one access token for the whole application, so every `connect` replaces the one in force and ends any other client's session, including UBI's own REST API test page in a browser tab. If a long-running script suddenly starts seeing 401s, something else connected.

## What is where

```text
src/tradingmachine/assets/
├── instruments.py         Instrument, TradeableInstrument, NonTradeableInstrument
├── equities.py            the six equity classes, one per UBI equity segment
├── fixed_income.py        the six fixed income classes
├── commodities.py         the six commodity classes
├── currencies.py          the six currency classes
├── funds.py               ExchangeTradedFund and InvestmentTrust, which trade like shares
├── mutual_funds.py        MutualFund, which is held rather than traded
├── exceptions.py          InstrumentError and its thirty-two subclasses
└── analysis/              thirteen classes of candle analysis that Instrument inherits

src/tradingmachine/ubi_client/
├── client.py              UnifiedBrokerInterface: connect, disconnect, status, get, post, …
└── exceptions.py          one error class per HTTP status code UBI returns

src/tradingmachine/utilities/
└── configuration.py       Configuration, which reads the environment and .env lazily

scripts/
├── gen_ref_pages.py       builds the API reference at documentation build time
└── documentation_hooks.py silences one griffe warning during a strict docs build

pyproject.toml             the library's metadata, dependencies and build backend
docs/                      the MkDocs site
.claude/notes/             one Markdown note per source file, holding the reasoning
```

The library is installable and the three packages are subpackages of `tradingmachine`, so every import is a full path from it: `from tradingmachine.assets import equities`. Nothing in the repository root is importable, which is what the `src/` directory is for.

This project keeps no explanatory comments in source files. Reasoning, trade-offs, dated live checks and the record of which alternative was turned down go into a sidecar note under `.claude/notes/`, mirroring the source tree, so `src/tradingmachine/assets/equities.py` is documented by `.claude/notes/src/tradingmachine/assets/equities.py.md`. Those notes are more detailed than the documentation site and are the place to look before changing anything.

## Tests and lint

There is no test suite. `pytest` is not in `requirements.txt` and is not installed, and that is not only inertia: exercising the order routes against UBI means placing real orders at a real broker. What verification exists is recorded in the sidecar notes, as live checks against a running UBI on a stated date, and each note says plainly whether any order was sent.

```bash
.venv/bin/ruff check .          # ruff 0.11.2, no config file, so default rules
.venv/bin/ruff format .
```

Unlike the sibling project, lint is clean on an untouched tree: `ruff check .` reports `All checks passed!` and `ruff format --check .` reports all 32 files already formatted. Keep it that way.

## Documentation

The `docs/` directory is a full Material for MkDocs site and is the authoritative reference. Narrative pages are hand-written; the API reference is generated from the docstrings at build time by `scripts/gen_ref_pages.py`, one page per module, so a new module appears without any edit anywhere.

```bash
.venv/bin/mkdocs serve           # http://127.0.0.1:8000, with live reload
.venv/bin/mkdocs build --strict  # broken links and references fail the build
```

Three pages are worth knowing about before you change anything. `docs/contributing/pitfalls.md` collects the things that have caught someone out, from the lot-size trap to what HTTP 504 means for an order. `docs/contributing/known-issues.md` separates what is actually broken, most of it in UBI, from what is merely surprising. `docs/contributing/adding-an-asset-class.md` walks through building the next family module in the pattern the existing six follow.
