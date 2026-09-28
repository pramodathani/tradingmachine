# src/tradingmachine/asset_baskets/__init__.py

The package was added on 2026-09-28 at the user's request, to hold baskets of instruments: portfolios, indices, and the contents of mutual funds and ETFs, all derived from one base class `AssetBasket`. The user said they were out of their depth on portfolio analysis and asked for guidance on which properties and methods to include. The plan was agreed in plan mode and is kept at `~/.claude/plans/i-want-to-add-idempotent-cupcake.md`.

Like the other packages, the `__init__.py` imports nothing, so importing the library never reaches for the network or the databases.

## Decisions taken with the user on 2026-09-28

| Question | Decision |
|---|---|
| Where members come from | The caller supplies them, and they are stored in the database, because some baskets, such as NSE indices, will be seeded ahead of time |
| Which database | MongoDB, left to Claude; see `basket_store.py.md` |
| Seeding | A generic CSV importer now, and scripts in `bin/` that download constituents and weights later |
| Inheriting analysis | Yes: a basket makes its own candles and inherits every analysis method |
| Scope | Everything in one pull request |
| The existing fund and index classes | Linked to their baskets through `constituents` rather than merged, left to Claude |

## What UBI offers and what it does not

UBI's instrument routes take a list when called with `POST`: `details`, `ltp`, `ohlc`, `quote` and `prices` answer `{"results": [...]}` with one entry per instrument, and a bad instrument fails only its own entry. `POST /api/orders/place` takes up to 500 orders in its list form. The package is built on these.

UBI stores no index constituents, no index weights, no ETF or mutual fund holdings and no net asset value history; the search of its code and databases found only equal-weight index names and iNAV index rows. That is why baskets live in this project's MongoDB and why the user supplies them.
